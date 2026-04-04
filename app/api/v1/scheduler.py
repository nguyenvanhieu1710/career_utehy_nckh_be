"""
Scheduler Monitoring API - Real-time monitoring for cron jobs
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.database import get_db
from app.services.crawler_config_service import CrawlerConfigService
from app.services.crawl_history_service import CrawlHistoryService
from app.utils.auth import get_current_user_permissions
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SchedulerHealthResponse(BaseModel):
    """Scheduler health status"""
    scheduler_running: bool
    total_jobs: int
    active_jobs: int
    next_executions: List[dict]
    last_execution: Optional[dict]


class JobExecutionLog(BaseModel):
    """Job execution log entry"""
    job_id: str
    source_id: str
    execution_time: str
    status: str
    duration_seconds: Optional[int]
    jobs_found: Optional[int]
    error_message: Optional[str]


class SchedulerMonitorResponse(BaseModel):
    """Complete scheduler monitoring data"""
    health: SchedulerHealthResponse
    recent_executions: List[JobExecutionLog]
    upcoming_jobs: List[dict]


@router.get("/scheduler/health", response_model=SchedulerHealthResponse)
async def get_scheduler_health(
    # permissions: List[str] = Depends(get_current_user_permissions)  # TODO: Uncomment for production
):
    """Get scheduler health status - Real-time monitoring"""
    
    # Temporarily disabled for testing
    # if "crawl_config.view" not in permissions and "*" not in permissions:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions"
    #     )
    
    try:
        from app.core.scheduler import cron_scheduler
        
        # Get all scheduled jobs
        jobs = cron_scheduler.get_scheduled_jobs()
        
        # Get next 5 executions
        next_executions = []
        for job in jobs[:5]:
            if job['next_run_time']:
                next_executions.append({
                    'job_id': job['id'],
                    'source_id': job['source_id'],
                    'next_run': job['next_run_time'],
                    'trigger': job['trigger']
                })
        
        # Check if scheduler is running
        scheduler_running = cron_scheduler.scheduler.running
        
        return SchedulerHealthResponse(
            scheduler_running=scheduler_running,
            total_jobs=len(jobs),
            active_jobs=len([j for j in jobs if j['next_run_time']]),
            next_executions=next_executions,
            last_execution=None  # Will be populated from crawl_history
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduler health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler health: {str(e)}"
        )


@router.get("/scheduler/monitor", response_model=SchedulerMonitorResponse)
async def get_scheduler_monitor(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    # permissions: List[str] = Depends(get_current_user_permissions)  # TODO: Uncomment for production
):
    """Get complete scheduler monitoring data"""
    
    # Temporarily disabled for testing
    # if "crawl_config.view" not in permissions and "*" not in permissions:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions"
    #     )
    
    try:
        from app.core.scheduler import cron_scheduler
        
        # Get health status
        jobs = cron_scheduler.get_scheduled_jobs()
        scheduler_running = cron_scheduler.scheduler.running
        
        # Get next executions
        next_executions = []
        for job in jobs:
            if job['next_run_time']:
                next_executions.append({
                    'job_id': job['id'],
                    'source_id': job['source_id'],
                    'next_run': job['next_run_time'],
                    'trigger': job['trigger']
                })
        
        # Get recent executions from crawl_history
        recent_result = await CrawlHistoryService.get_crawl_histories(
            db=db,
            status='all',
            page=1,
            limit=limit,
            sort_by='started_at',
            sort_order='desc'
        )
        
        recent_executions = []
        for history in recent_result['data']:
            recent_executions.append(JobExecutionLog(
                job_id=f"crawl_{history['source_id']}",
                source_id=history['source_id'],
                execution_time=history['started_at'],
                status=history['status'],
                duration_seconds=history['duration_seconds'],
                jobs_found=history['total_jobs_found'],
                error_message=history['error_message']
            ))
        
        health = SchedulerHealthResponse(
            scheduler_running=scheduler_running,
            total_jobs=len(jobs),
            active_jobs=len([j for j in jobs if j['next_run_time']]),
            next_executions=next_executions[:5],
            last_execution=recent_executions[0].dict() if recent_executions else None
        )
        
        return SchedulerMonitorResponse(
            health=health,
            recent_executions=recent_executions,
            upcoming_jobs=next_executions
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduler monitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler monitor: {str(e)}"
        )


@router.post("/scheduler/test-job")
async def test_scheduler_job(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    # permissions: List[str] = Depends(get_current_user_permissions)  # TODO: Uncomment for production
):
    """
    Test scheduler by setting a job to run in 1 minute
    Useful for testing without waiting for actual schedule
    """
    
    # Temporarily disabled for testing
    # if "crawl_config.update" not in permissions and "*" not in permissions:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions"
    #     )
    
    try:
        from app.core.scheduler import cron_scheduler
        from datetime import datetime, timedelta
        
        # Get current config
        config = await CrawlerConfigService.get_config_by_source_id(db, source_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crawler config not found"
            )
        
        # Calculate next minute
        now = datetime.now()
        next_minute = now + timedelta(minutes=1)
        test_cron = f"{next_minute.minute} {next_minute.hour} * * *"
        
        # Update config temporarily
        await CrawlerConfigService.update_config(
            db=db,
            source_id=source_id,
            cron_expression=test_cron,
            status='enabled'
        )
        
        # Reschedule job
        await cron_scheduler.schedule_crawl_job(
            source_id=source_id,
            cron_expression=test_cron,
            timezone=config.timezone or 'UTC'
        )
        
        return {
            "message": "Test job scheduled",
            "source_id": source_id,
            "test_cron": test_cron,
            "next_run": next_minute.isoformat(),
            "note": "Job will run in 1 minute. Check /scheduler/monitor for results."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling test job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule test job: {str(e)}"
        )


@router.get("/scheduler/logs")
async def get_scheduler_logs(
    source_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    # permissions: List[str] = Depends(get_current_user_permissions)  # TODO: Uncomment for production
):
    """Get scheduler execution logs with filtering"""
    
    # Temporarily disabled for testing
    # if "crawl_config.view" not in permissions and "*" not in permissions:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions"
    #     )
    
    try:
        result = await CrawlHistoryService.get_crawl_histories(
            db=db,
            source_id=source_id,
            status='all',
            page=1,
            limit=limit,
            sort_by='started_at',
            sort_order='desc'
        )
        
        logs = []
        for history in result['data']:
            logs.append({
                'id': history['id'],
                'source_id': history['source_id'],
                'source_name': history['source_name'],
                'started_at': history['started_at'],
                'completed_at': history['completed_at'],
                'status': history['status'],
                'duration_seconds': history['duration_seconds'],
                'jobs_found': history['total_jobs_found'],
                'jobs_created': history['jobs_created'],
                'jobs_updated': history['jobs_updated'],
                'success_rate': history['success_rate'],
                'error_message': history['error_message']
            })
        
        return {
            'logs': logs,
            'total': result['total'],
            'page': result['page'],
            'limit': result['limit']
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler logs: {str(e)}"
        )