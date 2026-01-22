from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, asc, or_, and_, func, select
from datetime import datetime, timedelta
from app.models.data_source import DataSource
from app.models.job import Job
from app.services.crawler_config_service import CrawlerConfigService
import logging

logger = logging.getLogger(__name__)

class DataSourceService:
    
    @staticmethod
    async def get_data_sources(
        db: AsyncSession,
        page: int = 1,
        limit: int = 10,
        search_keyword: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get paginated list of data sources with filters"""
        try:
            # Base query
            query = select(DataSource)
            
            # Apply filters
            if search_keyword:
                search_filter = f"%{search_keyword}%"
                query = query.where(
                    or_(
                        DataSource.name.ilike(search_filter),
                        DataSource.base_url.ilike(search_filter)
                    )
                )
            
            if status and status != "all":
                query = query.where(DataSource.status == status)
            
            # Apply sorting
            sort_column = getattr(DataSource, sort_by, DataSource.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Get total count
            count_query = select(func.count()).select_from(DataSource)
            if search_keyword:
                search_filter = f"%{search_keyword}%"
                count_query = count_query.where(
                    or_(
                        DataSource.name.ilike(search_filter),
                        DataSource.base_url.ilike(search_filter)
                    )
                )
            if status and status != "all":
                count_query = count_query.where(DataSource.status == status)
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * limit
            paginated_query = query.offset(offset).limit(limit)
            result = await db.execute(paginated_query)
            data_sources = result.scalars().all()
            
            # Calculate statistics for each data source
            enriched_data_sources = []
            for ds in data_sources:
                # Get job statistics
                job_stats_query = select(
                    func.count(Job.id).label('total_jobs'),
                    func.count(Job.id).filter(Job.created_at >= datetime.now() - timedelta(days=30)).label('recent_jobs')
                ).where(Job.source_id == ds.id)
                
                job_stats_result = await db.execute(job_stats_query)
                job_stats = job_stats_result.first()
                
                # Get crawler config info
                crawler_config = await CrawlerConfigService.get_config_by_source_id(db, str(ds.id))
                
                # Get latest crawl history for scheduling info
                from app.services.crawl_history_service import CrawlHistoryService
                next_run_at = await CrawlHistoryService.get_next_scheduled_crawl(db, str(ds.id))
                
                # Convert to dict and add statistics
                ds_dict = {
                    "id": str(ds.id),  # Convert UUID to string
                    "name": ds.name,
                    "base_url": ds.base_url,
                    "status": ds.status,
                    "last_crawled_at": ds.last_crawled_at.isoformat() if ds.last_crawled_at else None,
                    "created_at": ds.created_at.isoformat() if ds.created_at else None,
                    "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
                    
                    # Statistics
                    "total_records": job_stats.total_jobs or 0 if job_stats else 0,
                    "recent_records": job_stats.recent_jobs or 0 if job_stats else 0,
                    "success_rate": 95.0 if ds.status == "active" else 0.0,  # Mock for now
                    
                    # Crawler config info
                    "crawl_frequency": crawler_config.frequency if crawler_config else "daily",
                    "crawl_enabled": crawler_config.status == "enabled" if crawler_config else False,
                    "next_run_at": next_run_at.isoformat() if next_run_at else None,
                }
                
                enriched_data_sources.append(ds_dict)
            
            return {
                "data": enriched_data_sources,
                "total": total,
                "page": page,
                "limit": limit,
                "max_page": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error getting data sources: {str(e)}")
            raise e
    
    @staticmethod
    async def get_data_source_by_id(db: AsyncSession, data_source_id: str) -> Optional[DataSource]:
        """Get data source by ID"""
        try:
            query = select(DataSource).where(DataSource.id == data_source_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting data source {data_source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def create_data_source(
        db: AsyncSession,
        name: str,
        base_url: Optional[str] = None,
        status: str = "inactive",
        # Crawl config parameters
        crawl_frequency: str = "daily",
        crawl_enabled: bool = True
    ) -> DataSource:
        """Create new data source with crawler config"""
        try:
            data_source = DataSource(
                name=name,
                base_url=base_url,
                status=status,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(data_source)
            await db.commit()
            await db.refresh(data_source)
            
            # Create crawler config
            await CrawlerConfigService.create_config(
                db=db,
                source_id=str(data_source.id),
                frequency=crawl_frequency,
                status="enabled" if crawl_enabled else "disabled"
            )
            
            logger.info(f"Created data source with config: {data_source.name}")
            return data_source
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating data source: {str(e)}")
            raise e
    
    @staticmethod
    async def update_data_source(
        db: AsyncSession,
        data_source_id: str,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        status: Optional[str] = None,
        # Crawl config parameters
        crawl_frequency: Optional[str] = None,
        crawl_enabled: Optional[bool] = None
    ) -> Optional[DataSource]:
        """Update data source and crawler config"""
        try:
            query = select(DataSource).where(DataSource.id == data_source_id)
            result = await db.execute(query)
            data_source = result.scalar_one_or_none()
            
            if not data_source:
                return None
            
            # Update data source fields if provided
            if name is not None:
                data_source.name = name
            if base_url is not None:
                data_source.base_url = base_url
            if status is not None:
                data_source.status = status
            
            data_source.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(data_source)
            
            # Update crawler config if any crawl parameters provided
            if any([crawl_frequency is not None, crawl_enabled is not None]):
                crawl_status = None
                if crawl_enabled is not None:
                    crawl_status = "enabled" if crawl_enabled else "disabled"
                
                await CrawlerConfigService.update_config(
                    db=db,
                    source_id=data_source_id,
                    frequency=crawl_frequency,
                    status=crawl_status
                )
            
            logger.info(f"Updated data source: {data_source.name}")
            return data_source
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating data source {data_source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def delete_data_source(db: AsyncSession, data_source_id: str) -> bool:
        """Delete data source"""
        try:
            query = select(DataSource).where(DataSource.id == data_source_id)
            result = await db.execute(query)
            data_source = result.scalar_one_or_none()
            
            if not data_source:
                return False
            
            # Check if data source has jobs
            job_count_query = select(func.count(Job.id)).where(Job.source_id == data_source_id)
            job_count_result = await db.execute(job_count_query)
            job_count = job_count_result.scalar()
            
            if job_count > 0:
                raise ValueError(f"Cannot delete data source with {job_count} associated jobs")
            
            db.delete(data_source)
            await db.commit()
            
            logger.info(f"Deleted data source: {data_source.name}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting data source {data_source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def get_data_source_statistics(db: AsyncSession, data_source_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a data source"""
        try:
            query = select(DataSource).where(DataSource.id == data_source_id)
            result = await db.execute(query)
            data_source = result.scalar_one_or_none()
            
            if not data_source:
                return {}
            
            # Get job statistics by time periods
            now = datetime.utcnow()
            
            # Total jobs
            total_jobs_query = select(func.count(Job.id)).where(Job.source_id == data_source_id)
            total_jobs_result = await db.execute(total_jobs_query)
            total_jobs = total_jobs_result.scalar()
            
            # Jobs last 7 days
            jobs_7d_query = select(func.count(Job.id)).where(
                and_(
                    Job.source_id == data_source_id,
                    Job.created_at >= now - timedelta(days=7)
                )
            )
            jobs_7d_result = await db.execute(jobs_7d_query)
            jobs_7d = jobs_7d_result.scalar()
            
            # Jobs last 30 days
            jobs_30d_query = select(func.count(Job.id)).where(
                and_(
                    Job.source_id == data_source_id,
                    Job.created_at >= now - timedelta(days=30)
                )
            )
            jobs_30d_result = await db.execute(jobs_30d_query)
            jobs_30d = jobs_30d_result.scalar()
            
            stats = {
                "total_jobs": total_jobs or 0,
                "jobs_last_7_days": jobs_7d or 0,
                "jobs_last_30_days": jobs_30d or 0,
                "last_crawl": data_source.last_crawled_at.isoformat() if data_source.last_crawled_at else None,
                "status": data_source.status,
                "success_rate": 95.0 if data_source.status == "active" else 0.0  # Mock for now
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics for data source {data_source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def update_last_crawled(db: AsyncSession, data_source_id: str) -> bool:
        """Update last crawled timestamp"""
        try:
            query = select(DataSource).where(DataSource.id == data_source_id)
            result = await db.execute(query)
            data_source = result.scalar_one_or_none()
            
            if not data_source:
                return False
            
            data_source.last_crawled_at = datetime.utcnow()
            data_source.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info(f"Updated last crawled time for data source: {data_source.name}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last crawled for data source {data_source_id}: {str(e)}")
            raise e