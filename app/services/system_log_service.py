from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_log import SystemLog
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SystemLogService:
    @staticmethod
    async def log(
        db: AsyncSession,
        action_type: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> SystemLog:
        """Create a new system log entry"""
        try:
            new_log = SystemLog(
                user_id=user_id,
                action_type=action_type,
                description=description,
                path=path,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                duration_ms=duration_ms,
                metadata_json=metadata_json
            )
            db.add(new_log)
            await db.commit()
            await db.refresh(new_log)
            return new_log
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating system log: {str(e)}")
            # We don't raise here to prevent logging failures from breaking the app
            return None

    @staticmethod
    async def log_visit(
        db: AsyncSession,
        path: str,
        method: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Shorthand for logging a visit"""
        return await SystemLogService.log(
            db=db,
            action_type='visit',
            user_id=user_id,
            path=path,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            description=f"User visited {path}"
        )
