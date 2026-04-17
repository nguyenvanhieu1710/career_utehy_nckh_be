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
            
            # Register MinIO auto-import task (Every 30 mins)
            self.scheduler.add_job(
                func=self.execute_auto_import_from_minio,
                trigger='interval',
                minutes=30,
                id='minio_auto_import',
                name='Automatic import from MinIO stage3 folders',
                replace_existing=True
            )
            logger.info("📅 Scheduled MinIO auto-import task (every 30 mins)")
            
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
    
    async def execute_auto_import_from_minio(self):
        """Periodic task to scan and import jobs from MinIO"""
        logger.info("🔍 [Auto Import] Starting smart scan for MinIO objects...")
        async with SessionLocal() as db:
            from app.services.import_job_service import ImportJobService
            try:
                result = await ImportJobService.smart_scan_and_import(db)
                if result.get("new_processed", 0) > 0:
                    logger.info(f"✨ [Auto Import] Completed: {result}")
                else:
                    logger.info(f"ℹ️ [Auto Import] No new Stage 3 files found.")
            except Exception as e:
                logger.error(f"💣 [Auto Import] Task failed: {str(e)}")
    
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
        """Execute crawl by calling crawler-service API dynamically"""
        logger.info(f"🕷️ Starting crawl task for configuration: {source_id}")
        
        try:
            async with SessionLocal() as db:
                from app.services.crawler_config_service import CrawlerConfigService
                
                # Fetch config including the new crawler_payload
                config = await CrawlerConfigService.get_config_by_source_id(db, source_id)
                if not config:
                    raise Exception(f"Crawler config for source {source_id} not found")
                
                # Update last_scheduled_at
                await CrawlerConfigService.update_last_scheduled(db, source_id)
                
                payload = config.crawler_payload
                if not payload:
                    logger.warning(f"⚠️ No crawler_payload found for {source_id}, skipping.")
                    return
                
            # CRAWLER API URL (default to localhost:8001 if not set)
            crawler_url = os.getenv('CRAWLER_SERVICE_URL')
            
            # Use /push-job endpoint for all stages
            endpoint = "/push-job"
            stage = payload.get('stage', 1)
            
            # Ensure required fields for Crawler API
            prepared_payload = payload.copy()
            if 'stage' not in prepared_payload:
                prepared_payload['stage'] = stage
            
            if 'url_web' not in prepared_payload:
                # Use source's base_url if url_web is missing in payload
                prepared_payload['url_web'] = config.base_url or ""
            
            # Call Crawler API
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minutes for long crawl tasks
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{crawler_url}{endpoint}"
                
                logger.info(f"📡 Calling Crawler API: {url} (Stage: {prepared_payload.get('stage')})")
                
                async with session.post(url, json=prepared_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Crawler accepted job: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        error_msg = f"Crawler API returned {response.status}: {error_text}"
                        logger.error(f"❌ Crawler API failed: {error_msg}")
                        raise Exception(error_msg)
        
        except asyncio.TimeoutError:
            error_msg = "Crawler request timed out"
            logger.error(f"⏰ {error_msg}")
            raise Exception(error_msg)
        
        except Exception as e:
            logger.error(f"❌ Crawl execution failed: {e}")
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