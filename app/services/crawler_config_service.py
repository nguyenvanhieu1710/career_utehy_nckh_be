from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.crawler_config import CrawlerConfig
import logging

logger = logging.getLogger(__name__)

class CrawlerConfigService:
    
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
    async def create_config(
        db: AsyncSession,
        source_id: str,
        frequency: str = "daily",
        status: str = "enabled"
    ) -> CrawlerConfig:
        """Create new crawler config"""
        try:
            config = CrawlerConfig(
                source_id=source_id,
                frequency=frequency,
                status=status,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(config)
            await db.commit()
            await db.refresh(config)
            
            logger.info(f"Created crawler config for source: {source_id}")
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
        status: Optional[str] = None
    ) -> Optional[CrawlerConfig]:
        """Update crawler config"""
        try:
            query = select(CrawlerConfig).where(CrawlerConfig.source_id == source_id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()
            
            if not config:
                return None
            
            # Update fields if provided
            if frequency is not None:
                config.frequency = frequency
            if status is not None:
                config.status = status
            
            config.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(config)
            
            logger.info(f"Updated crawler config for source: {source_id}")
            return config
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating crawler config for source {source_id}: {str(e)}")
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