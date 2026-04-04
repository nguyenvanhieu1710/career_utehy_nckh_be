"""
Crawl Tracker Utility
Provides easy integration with crawl history tracking for existing crawl processes
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.crawl_history_service import CrawlHistoryService
from app.models.crawl_history import CrawlHistory
from datetime import datetime
import logging
import time
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class CrawlTracker:
    """
    Context manager for tracking crawl sessions
    
    Usage:
    async with CrawlTracker(db, source_id) as tracker:
        # Your crawl logic here
        tracker.update_progress(jobs_found=10)
        tracker.increment_created()
        # ... crawl logic ...
        # Automatically completes on exit
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        source_id: str,
        crawler_version: str = "1.0.0",
        user_agent: str = "Career-Crawler/1.0",
        next_run_at: Optional[datetime] = None  # datetime for next scheduled run
    ):
        self.db = db
        self.source_id = source_id
        self.crawler_version = crawler_version
        self.user_agent = user_agent
        self.next_run_at = next_run_at
        self.crawl_history: Optional[CrawlHistory] = None
        self.start_time = None
        
        # Progress tracking
        self.jobs_found = 0
        self.jobs_created = 0
        self.jobs_updated = 0
        self.jobs_skipped = 0
        self.jobs_failed = 0
        self.pages_crawled = 0
        self.error_count = 0
        self.response_times = []
    
    async def __aenter__(self):
        """Start crawl session"""
        try:
            self.start_time = time.time()
            self.crawl_history = await CrawlHistoryService.create_crawl_session(
                db=self.db,
                source_id=self.source_id,
                crawler_version=self.crawler_version,
                user_agent=self.user_agent,
                next_run_at=self.next_run_at
            )
            logger.info(f"Started crawl tracking session: {self.crawl_history.id}")
            return self
        except Exception as e:
            logger.error(f"Failed to start crawl tracking: {str(e)}")
            raise e
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete crawl session"""
        if not self.crawl_history:
            return
        
        try:
            # Determine status based on exception
            if exc_type is not None:
                status = 'failed'
                error_message = str(exc_val) if exc_val else "Unknown error occurred"
            else:
                status = 'completed'
                error_message = None
            
            # Update final statistics
            await self.update_progress()
            
            # Complete the session
            await CrawlHistoryService.complete_crawl_session(
                db=self.db,
                crawl_id=str(self.crawl_history.id),
                status=status,
                error_message=error_message
            )
            
            logger.info(f"Completed crawl tracking session: {self.crawl_history.id} with status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to complete crawl tracking: {str(e)}")
    
    async def update_progress(self, **kwargs):
        """Update crawl progress"""
        if not self.crawl_history:
            return
        
        try:
            # Calculate average response time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else None
            
            # Prepare update data
            update_data = {
                'total_jobs_found': self.jobs_found,
                'jobs_created': self.jobs_created,
                'jobs_updated': self.jobs_updated,
                'jobs_skipped': self.jobs_skipped,
                'jobs_failed': self.jobs_failed,
                'pages_crawled': self.pages_crawled,
                'error_count': self.error_count,
                'avg_response_time_ms': avg_response_time,
                **kwargs  # Allow custom updates
            }
            
            await CrawlHistoryService.update_crawl_progress(
                db=self.db,
                crawl_id=str(self.crawl_history.id),
                **update_data
            )
            
        except Exception as e:
            logger.error(f"Failed to update crawl progress: {str(e)}")
    
    def increment_found(self, count: int = 1):
        """Increment jobs found counter"""
        self.jobs_found += count
    
    def increment_created(self, count: int = 1):
        """Increment jobs created counter"""
        self.jobs_created += count
    
    def increment_updated(self, count: int = 1):
        """Increment jobs updated counter"""
        self.jobs_updated += count
    
    def increment_skipped(self, count: int = 1):
        """Increment jobs skipped counter"""
        self.jobs_skipped += count
    
    def increment_failed(self, count: int = 1):
        """Increment jobs failed counter"""
        self.jobs_failed += count
    
    def increment_pages(self, count: int = 1):
        """Increment pages crawled counter"""
        self.pages_crawled += count
    
    def increment_errors(self, count: int = 1):
        """Increment error counter"""
        self.error_count += count
    
    def add_response_time(self, response_time_ms: float):
        """Add response time for average calculation"""
        self.response_times.append(response_time_ms)
        
        # Keep only last 100 response times to avoid memory issues
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
    
    async def log_error(self, error_message: str, increment_counter: bool = True):
        """Log an error and optionally increment error counter"""
        logger.error(f"Crawl error in session {self.crawl_history.id if self.crawl_history else 'unknown'}: {error_message}")
        
        if increment_counter:
            self.increment_errors()
    
    @property
    def crawl_id(self) -> Optional[str]:
        """Get current crawl session ID"""
        return str(self.crawl_history.id) if self.crawl_history else None
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0
        return time.time() - self.start_time


# Convenience functions for simple usage
async def start_crawl_session(
    db: AsyncSession,
    source_id: str,
    crawler_version: str = "1.0.0",
    next_run_at: Optional[datetime] = None
) -> str:
    """Start a new crawl session and return the crawl ID"""
    crawl_history = await CrawlHistoryService.create_crawl_session(
        db=db,
        source_id=source_id,
        crawler_version=crawler_version,
        next_run_at=next_run_at
    )
    return str(crawl_history.id)

async def update_crawl_stats(
    db: AsyncSession,
    crawl_id: str,
    **stats
) -> bool:
    """Update crawl statistics"""
    try:
        await CrawlHistoryService.update_crawl_progress(
            db=db,
            crawl_id=crawl_id,
            **stats
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update crawl stats: {str(e)}")
        return False

async def complete_crawl_session(
    db: AsyncSession,
    crawl_id: str,
    status: str = 'completed',
    error_message: Optional[str] = None
) -> bool:
    """Complete a crawl session"""
    try:
        await CrawlHistoryService.complete_crawl_session(
            db=db,
            crawl_id=crawl_id,
            status=status,
            error_message=error_message
        )
        return True
    except Exception as e:
        logger.error(f"Failed to complete crawl session: {str(e)}")
        return False