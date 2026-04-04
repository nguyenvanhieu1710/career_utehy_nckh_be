"""
Cron Scheduler for automated crawling jobs
"""
import asyncio
import logging
import os
from typing import List
from datetime import datetime

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.services.crawler_config_service import CrawlerConfigService

logger = logging.getLogger(__name__)


class CronScheduler:
    """Manages cron jobs for automated crawling"""
    
    def __init__(self):
        """Initialize scheduler with configuration"""
        # Configure APScheduler
        jobstores = {'default': MemoryJobStore()}
        executors = {'default': AsyncIOExecutor()}
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # Crawl service configuration
        self.crawl_service_url = os.getenv('CRAWL_SERVICE_URL', 'http://localhost:3000')
        
    async def start(self):
        """Start the scheduler and load active jobs"""
        try:
            self.scheduler.start()
            logger.info("🚀 Cron Scheduler started")
            
            # Load active jobs from database
            await self.load_active_jobs()
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")
            raise e
    
    async def stop(self):
        """Stop the scheduler gracefully"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("🛑 Cron Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}")
    
    async def load_active_jobs(self):
        """Load all active crawler configs and schedule them"""
        try:
            async with SessionLocal() as db:
                configs = await CrawlerConfigService.get_active_configs(db)
                
                logger.info(f"📋 Loading {len(configs)} active crawler configs")
                
                for config in configs:
                    await self.schedule_crawl_job(
                        source_id=config.source_id,
                        cron_expression=config.cron_expression,
                        timezone=config.timezone
                    )
                
                logger.info(f"✅ Scheduled {len(configs)} crawl jobs")
                
        except Exception as e:
            logger.error(f"❌ Failed to load active jobs: {e}")
    
    async def schedule_crawl_job(self, source_id: str, cron_expression: str, timezone: str = 'UTC'):
        """Schedule a single crawl job"""
        try:
            job_id = f"crawl_{source_id}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Create cron trigger
            trigger = CronTrigger.from_crontab(cron_expression, timezone=timezone)
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self.execute_crawl,
                trigger=trigger,
                id=job_id,
                args=[source_id],
                name=f"Crawl job for source {source_id}",
                replace_existing=True
            )
            
            logger.info(f"📅 Scheduled crawl job: {job_id} with cron: {cron_expression}")
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule job for source {source_id}: {e}")
            raise e
    
    async def unschedule_crawl_job(self, source_id: str) -> bool:
        """Remove a scheduled crawl job"""
        try:
            job_id = f"crawl_{source_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"🗑️ Unscheduled crawl job: {job_id}")
                return True
            else:
                logger.warning(f"⚠️ Job not found: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to unschedule job for source {source_id}: {e}")
            return False
    
    async def execute_crawl(self, source_id: str):
        """Execute crawl by calling crawl-careers API"""
        logger.info(f"🕷️ Starting crawl for source: {source_id}")
        
        try:
            # Get source info to determine which API to call
            async with SessionLocal() as db:
                from app.services.data_source_service import DataSourceService
                
                # Update last_scheduled_at
                await CrawlerConfigService.update_last_scheduled(db, source_id)
                
                # Get source details
                source = await DataSourceService.get_data_source_by_id(db, source_id)
                if not source:
                    raise Exception(f"Data source {source_id} not found")
                
                source_name = source.name.lower() if source.name else 'jobgo'
            
            # Map source name to API endpoint and payload
            api_config = self._get_api_config(source_name)
            
            # Call crawl-careers API
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.crawl_service_url}{api_config['endpoint']}"
                
                logger.info(f"📡 Calling crawl API: {url} for source: {source_name}")
                
                async with session.post(url, json=api_config['payload']) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Crawl completed for source {source_id} ({source_name}): {result}")
                        return result
                    else:
                        error_text = await response.text()
                        error_msg = f"Crawl API returned {response.status}: {error_text}"
                        logger.error(f"❌ Crawl API failed for source {source_id}: {error_msg}")
                        raise Exception(error_msg)
        
        except asyncio.TimeoutError:
            error_msg = "Crawl request timed out"
            logger.error(f"⏰ {error_msg} for source {source_id}")
            raise Exception(error_msg)
        
        except Exception as e:
            logger.error(f"❌ Crawl execution failed for source {source_id}: {e}")
            raise e
    
    def _get_api_config(self, source_name: str) -> dict:
        """Get API endpoint and payload based on source name"""
        
        # Map source names to crawl-careers API endpoints
        source_mapping = {
            'jobgo': {
                'endpoint': '/api/crawl/jobgo',
                'payload': {
                    'saveToDb': True,
                    'maxPages': 5  # Configurable
                }
            },
            'vietnamworks': {
                'endpoint': '/api/crawl/vietnamworks',
                'payload': {
                    'saveToDb': True
                }
            },
            'jobsgo': {  # Alternative name
                'endpoint': '/api/crawl/jobgo',
                'payload': {
                    'saveToDb': True,
                    'maxPages': 5
                }
            }
        }
        
        # Get config for source, default to jobgo if not found
        config = source_mapping.get(source_name)
        
        if not config:
            logger.warning(f"⚠️ Unknown source name: {source_name}, using default (jobgo)")
            config = source_mapping['jobgo']
        
        return config
    
    async def trigger_crawl_now(self, source_id: str):
        """Manually trigger a crawl job immediately"""
        try:
            logger.info(f"🚀 Manual trigger crawl for source: {source_id}")
            result = await self.execute_crawl(source_id)
            return result
        except Exception as e:
            logger.error(f"❌ Manual crawl failed for source {source_id}: {e}")
            raise e
    
    def get_scheduled_jobs(self) -> List[dict]:
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'source_id': job.args[0] if job.args else None
            })
        return jobs
    
    def _job_executed(self, event):
        """Handle successful job execution"""
        logger.info(f"✅ Job executed successfully: {event.job_id}")
    
    def _job_error(self, event):
        """Handle job execution error"""
        logger.error(f"❌ Job execution failed: {event.job_id} - {event.exception}")


# Global scheduler instance
cron_scheduler = CronScheduler()