from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.database import get_db
from app.services import statistical_service
from app.utils.auth import get_current_user_permissions
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """
    Get statistics for the admin dashboard chart.
    Required permission: dashboard.view or *
    """
    # Check permissions
    if "dashboard.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view dashboard statistics"
        )
    
    try:
        data = await statistical_service.get_admin_dashboard_stats(days=days, db=db)
        return {
            "status": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
