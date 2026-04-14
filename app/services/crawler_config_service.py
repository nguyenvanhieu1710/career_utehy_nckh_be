from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.crawler_config import CrawlerConfig
import logging

logger = logging.getLogger(__name__)

class CrawlerConfigService:
    
    # Frequency ↔ Cron Expression mapping
    FREQUENCY_TO_CRON = {
        'hourly': '0 * * * *',      # Every hour at minute 0
        'daily': '0 2 * * *',       # Daily at 2 AM
        'weekly': '0 2 * * 0',      # Weekly on Sunday at 2 AM
    }
    
    CRON_TO_FREQUENCY = {
        '0 * * * *': 'hourly',
        '0 2 * * *': 'daily', 
        '0 2 * * 0': 'weekly',
    }
    
    @staticmethod
    def sync_frequency_and_cron(
        frequency: Optional[str] = None, 
        cron_expression: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Always keep frequency and cron_expression in sync
        Returns: (frequency, cron_expression)
        """
        
        # If frequency is provided, convert to cron
        if frequency and frequency in CrawlerConfigService.FREQUENCY_TO_CRON:
            cron = CrawlerConfigService.FREQUENCY_TO_CRON[frequency]
            return frequency, cron
        
        # If cron is provided, try to convert to frequency (best match)
        if cron_expression:
            frequency_match = CrawlerConfigService.CRON_TO_FREQUENCY.get(cron_expression)
            if frequency_match:
                return frequency_match, cron_expression
            else:
                # Custom cron expression - default to 'daily' frequency
                return 'daily', cron_expression
        
        # Default fallback
        return 'daily', '0 2 * * *'
    
    @staticmethod
    async def get_config_by_source_id(db: AsyncSession, source_id: str) -> Optional[CrawlerConfig]:
        """Get crawler config by source ID"""
        try:
            query = select(CrawlerConfig).where(CrawlerConfig.source_id == source_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting crawler config for source {source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def get_active_configs(db: AsyncSession) -> list[CrawlerConfig]:
        """Get all active crawler configs for scheduling"""
        try:
            query = select(CrawlerConfig).where(
                CrawlerConfig.status == 'enabled',
                CrawlerConfig.cron_expression.isnot(None)
            )
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active crawler configs: {str(e)}")
            raise e
    
    @staticmethod
    async def create_config(
        db: AsyncSession,
        source_id: str,
        frequency: str = "daily",
        status: str = "enabled",
        cron_expression: Optional[str] = None,
        timezone: str = "UTC",
        crawler_payload: Optional[Dict[str, Any]] = None
    ) -> CrawlerConfig:
        """Create new crawler config with auto-sync"""
        try:
            # Auto-sync frequency and cron_expression
            synced_frequency, synced_cron = CrawlerConfigService.sync_frequency_and_cron(
                frequency, cron_expression
            )
            
            config = CrawlerConfig(
                source_id=source_id,
                frequency=synced_frequency,
                status=status,
                cron_expression=synced_cron,
                timezone=timezone,
                crawler_payload=crawler_payload,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(config)
            await db.commit()
            await db.refresh(config)
            
            logger.info(f"Created crawler config for source: {source_id} with schedule: {synced_cron}")
            return config
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating crawler config: {str(e)}")
            raise e
    
    @staticmethod
    async def update_config(
        db: AsyncSession,
        source_id: str,
        frequency: Optional[str] = None,
        status: Optional[str] = None,
        cron_expression: Optional[str] = None,
        timezone: Optional[str] = None,
        crawler_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[CrawlerConfig]:
        """Update crawler config with auto-sync"""
        try:
            query = select(CrawlerConfig).where(CrawlerConfig.source_id == source_id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()
            
            if not config:
                return None
            
            # Auto-sync frequency and cron_expression if either is provided
            if frequency is not None or cron_expression is not None:
                current_frequency = frequency if frequency is not None else config.frequency
                current_cron = cron_expression if cron_expression is not None else config.cron_expression
                
                synced_frequency, synced_cron = CrawlerConfigService.sync_frequency_and_cron(
                    current_frequency, current_cron
                )
                
                config.frequency = synced_frequency
                config.cron_expression = synced_cron
            
            # Update other fields if provided
            if status is not None:
                config.status = status
            if timezone is not None:
                config.timezone = timezone
            if crawler_payload is not None:
                config.crawler_payload = crawler_payload
            
            config.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(config)
            
            logger.info(f"Updated crawler config for source: {source_id} with schedule: {config.cron_expression}")
            return config
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating crawler config for source {source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def update_last_scheduled(
        db: AsyncSession,
        source_id: str,
        scheduled_at: datetime = None
    ) -> bool:
        """Update last_scheduled_at timestamp"""
        try:
            query = select(CrawlerConfig).where(CrawlerConfig.source_id == source_id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()
            
            if not config:
                return False
            
            config.last_scheduled_at = scheduled_at or datetime.utcnow()
            await db.commit()
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last_scheduled_at for source {source_id}: {str(e)}")
            raise e
    
    @staticmethod
    async def delete_config(db: AsyncSession, source_id: str) -> bool:
        """Delete crawler config"""
        try:
            query = select(CrawlerConfig).where(CrawlerConfig.source_id == source_id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()
            
            if not config:
                return False
            
            await db.delete(config)
            await db.commit()
            
            logger.info(f"Deleted crawler config for source: {source_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting crawler config for source {source_id}: {str(e)}")
            raise e