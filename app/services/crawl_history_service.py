from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, asc, or_, and_, func, select
from datetime import datetime, timedelta
from app.models.crawl_history import CrawlHistory
from app.models.data_source import DataSource
import logging
import uuid

logger = logging.getLogger(__name__)

class CrawlHistoryService:
    
    @staticmethod
    async def create_crawl_session(
        db: AsyncSession,
        source_id: str,
        crawler_version: str = "1.0.0",
        user_agent: str = "Career-Crawler/1.0",
        last_run_at: Optional[datetime] = None,
        next_run_at: Optional[datetime] = None
    ) -> CrawlHistory:
        """Create a new crawl session"""
        try:
            crawl_history = CrawlHistory(
                source_id=source_id,
                started_at=datetime.utcnow(),
                status='running',
                crawler_version=crawler_version,
                user_agent=user_agent,
                last_run_at=last_run_at or datetime.utcnow(),
                next_run_at=next_run_at
            )
            
            db.add(crawl_history)
            await db.commit()
            await db.refresh(crawl_history)
            
            logger.info(f"Created crawl session: {crawl_history.id} for source: {source_id}")
            return crawl_history
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating crawl session: {str(e)}")
            raise e
    
    @staticmethod
    async def update_crawl_progress(
        db: AsyncSession,
        crawl_id: str,
        **kwargs
    ) -> Optional[CrawlHistory]:
        """Update crawl progress with new statistics"""
        try:
            query = select(CrawlHistory).where(CrawlHistory.id == crawl_id)
            result = await db.execute(query)
            crawl_history = result.scalar_one_or_none()
            
            if not crawl_history:
                logger.warning(f"Crawl history not found: {crawl_id}")
                return None
            
            # Update fields if provided
            for field, value in kwargs.items():
                if hasattr(crawl_history, field):
                    setattr(crawl_history, field, value)
            
            crawl_history.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(crawl_history)
            
            logger.debug(f"Updated crawl progress: {crawl_id}")
            return crawl_history
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating crawl progress {crawl_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def complete_crawl_session(
        db: AsyncSession,
        crawl_id: str,
        status: str = 'completed',
        error_message: Optional[str] = None
    ) -> Optional[CrawlHistory]:
        """Complete a crawl session"""
        try:
            query = select(CrawlHistory).where(CrawlHistory.id == crawl_id)
            result = await db.execute(query)
            crawl_history = result.scalar_one_or_none()
            
            if not crawl_history:
                logger.warning(f"Crawl history not found: {crawl_id}")
                return None
            
            # Calculate duration
            completed_at = datetime.utcnow()
            duration = (completed_at - crawl_history.started_at).total_seconds()
            
            # Update completion fields
            crawl_history.completed_at = completed_at
            crawl_history.duration_seconds = int(duration)
            crawl_history.status = status
            crawl_history.updated_at = completed_at
            
            if error_message:
                crawl_history.error_message = error_message
            
            await db.commit()
            await db.refresh(crawl_history)
            
            logger.info(f"Completed crawl session: {crawl_id} with status: {status}")
            return crawl_history
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error completing crawl session {crawl_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def get_crawl_histories(
        db: AsyncSession,
        source_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "started_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get paginated crawl histories with filters"""
        try:
            # Base query
            query = select(CrawlHistory)
            
            # Apply filters
            if source_id:
                query = query.where(CrawlHistory.source_id == source_id)
            
            if status and status != "all":
                query = query.where(CrawlHistory.status == status)
            
            # Apply sorting
            sort_column = getattr(CrawlHistory, sort_by, CrawlHistory.started_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Get total count
            count_query = select(func.count()).select_from(CrawlHistory)
            if source_id:
                count_query = count_query.where(CrawlHistory.source_id == source_id)
            if status and status != "all":
                count_query = count_query.where(CrawlHistory.status == status)
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * limit
            paginated_query = query.offset(offset).limit(limit)
            result = await db.execute(paginated_query)
            crawl_histories = result.scalars().all()
            
            # Convert to dict format
            histories_data = []
            for history in crawl_histories:
                history_dict = {
                    "id": str(history.id),
                    "source_id": str(history.source_id),
                    "started_at": history.started_at.isoformat() if history.started_at else None,
                    "completed_at": history.completed_at.isoformat() if history.completed_at else None,
                    "duration_seconds": history.duration_seconds,
                    "last_run_at": history.last_run_at.isoformat() if history.last_run_at else None,
                    "next_run_at": history.next_run_at.isoformat() if history.next_run_at else None,
                    "status": history.status,
                    "total_jobs_found": history.total_jobs_found,
                    "jobs_created": history.jobs_created,
                    "jobs_updated": history.jobs_updated,
                    "jobs_skipped": history.jobs_skipped,
                    "jobs_failed": history.jobs_failed,
                    "error_count": history.error_count,
                    "error_message": history.error_message,
                    "pages_crawled": history.pages_crawled,
                    "avg_response_time_ms": history.avg_response_time_ms,
                    "success_rate": history.success_rate,
                    "crawler_version": history.crawler_version,
                    "created_at": history.created_at.isoformat() if history.created_at else None,
                    "updated_at": history.updated_at.isoformat() if history.updated_at else None
                }
                histories_data.append(history_dict)
            
            return {
                "data": histories_data,
                "total": total,
                "page": page,
                "limit": limit,
                "max_page": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error getting crawl histories: {str(e)}")
            raise e
    
    @staticmethod
    async def get_crawl_history_by_id(
        db: AsyncSession,
        crawl_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed crawl history by ID"""
        try:
            query = select(CrawlHistory).where(CrawlHistory.id == crawl_id)
            result = await db.execute(query)
            crawl_history = result.scalar_one_or_none()
            
            if not crawl_history:
                return None
            
            # Get source information
            source_query = select(DataSource).where(DataSource.id == crawl_history.source_id)
            source_result = await db.execute(source_query)
            source = source_result.scalar_one_or_none()
            
            return {
                "id": str(crawl_history.id),
                "source_id": str(crawl_history.source_id),
                "source_name": source.name if source else "Unknown",
                "source_base_url": source.base_url if source else None,
                "started_at": crawl_history.started_at.isoformat() if crawl_history.started_at else None,
                "completed_at": crawl_history.completed_at.isoformat() if crawl_history.completed_at else None,
                "duration_seconds": crawl_history.duration_seconds,
                "last_run_at": crawl_history.last_run_at.isoformat() if crawl_history.last_run_at else None,
                "next_run_at": crawl_history.next_run_at.isoformat() if crawl_history.next_run_at else None,
                "status": crawl_history.status,
                "total_jobs_found": crawl_history.total_jobs_found,
                "jobs_created": crawl_history.jobs_created,
                "jobs_updated": crawl_history.jobs_updated,
                "jobs_skipped": crawl_history.jobs_skipped,
                "jobs_failed": crawl_history.jobs_failed,
                "error_count": crawl_history.error_count,
                "error_message": crawl_history.error_message,
                "pages_crawled": crawl_history.pages_crawled,
                "avg_response_time_ms": crawl_history.avg_response_time_ms,
                "success_rate": crawl_history.success_rate,
                "crawler_version": crawl_history.crawler_version,
                "user_agent": crawl_history.user_agent,
                "created_at": crawl_history.created_at.isoformat() if crawl_history.created_at else None,
                "updated_at": crawl_history.updated_at.isoformat() if crawl_history.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting crawl history {crawl_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def get_crawl_statistics(
        db: AsyncSession,
        source_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get crawl statistics for the last N days"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query
            query = select(CrawlHistory).where(CrawlHistory.started_at >= start_date)
            
            if source_id:
                query = query.where(CrawlHistory.source_id == source_id)
            
            result = await db.execute(query)
            histories = result.scalars().all()
            
            # Calculate statistics
            total_crawls = len(histories)
            successful_crawls = len([h for h in histories if h.status == 'completed'])
            failed_crawls = len([h for h in histories if h.status == 'failed'])
            running_crawls = len([h for h in histories if h.status == 'running'])
            
            total_jobs_found = sum(h.total_jobs_found or 0 for h in histories)
            total_jobs_created = sum(h.jobs_created or 0 for h in histories)
            total_jobs_updated = sum(h.jobs_updated or 0 for h in histories)
            
            # Calculate averages
            completed_histories = [h for h in histories if h.duration_seconds is not None]
            avg_duration = sum(h.duration_seconds for h in completed_histories) / len(completed_histories) if completed_histories else 0
            
            success_rate = (successful_crawls / total_crawls * 100) if total_crawls > 0 else 0
            
            return {
                "period_days": days,
                "total_crawls": total_crawls,
                "successful_crawls": successful_crawls,
                "failed_crawls": failed_crawls,
                "running_crawls": running_crawls,
                "success_rate": round(success_rate, 2),
                "total_jobs_found": total_jobs_found,
                "total_jobs_created": total_jobs_created,
                "total_jobs_updated": total_jobs_updated,
                "avg_duration_seconds": round(avg_duration, 2),
                "last_crawl": histories[0].started_at.isoformat() if histories else None
            }
            
        except Exception as e:
            logger.error(f"Error getting crawl statistics: {str(e)}")
            raise e
    
    @staticmethod
    async def cancel_running_crawls(
        db: AsyncSession,
        source_id: Optional[str] = None
    ) -> int:
        """Cancel all running crawls for a source or all sources"""
        try:
            query = select(CrawlHistory).where(CrawlHistory.status == 'running')
            
            if source_id:
                query = query.where(CrawlHistory.source_id == source_id)
            
            result = await db.execute(query)
            running_crawls = result.scalars().all()
            
            cancelled_count = 0
            for crawl in running_crawls:
                crawl.status = 'cancelled'
                crawl.completed_at = datetime.utcnow()
                crawl.duration_seconds = int((crawl.completed_at - crawl.started_at).total_seconds())
                crawl.updated_at = datetime.utcnow()
                cancelled_count += 1
            
            await db.commit()
            
            logger.info(f"Cancelled {cancelled_count} running crawls")
            return cancelled_count
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cancelling running crawls: {str(e)}")
            raise e
    
    @staticmethod
    async def get_next_scheduled_crawl(
        db: AsyncSession,
        source_id: str
    ) -> Optional[datetime]:
        """Get the next scheduled crawl time for a data source"""
        try:
            # Get the most recent crawl history for this source
            query = select(CrawlHistory).where(
                CrawlHistory.source_id == source_id
            ).order_by(desc(CrawlHistory.started_at)).limit(1)
            
            result = await db.execute(query)
            latest_crawl = result.scalar_one_or_none()
            
            if latest_crawl and latest_crawl.next_run_at:
                return latest_crawl.next_run_at
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next scheduled crawl for source {source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def update_next_crawl_schedule(
        db: AsyncSession,
        source_id: str,
        next_run_at: datetime,
        frequency: str = "daily"
    ) -> bool:
        """Update the next crawl schedule for a data source"""
        try:
            # Get the most recent crawl history for this source
            query = select(CrawlHistory).where(
                CrawlHistory.source_id == source_id
            ).order_by(desc(CrawlHistory.started_at)).limit(1)
            
            result = await db.execute(query)
            latest_crawl = result.scalar_one_or_none()
            
            if latest_crawl:
                latest_crawl.next_run_at = next_run_at
                latest_crawl.updated_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Updated next crawl schedule for source {source_id} to {next_run_at}")
                return True
            
            return False
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating next crawl schedule for source {source_id}: {str(e)}")
            raise e