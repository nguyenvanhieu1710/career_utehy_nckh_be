from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.services.crawl_history_service import CrawlHistoryService
from app.utils.auth import get_current_user_permissions
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class CrawlHistoryResponse(BaseModel):
    id: str
    source_id: str
    source_name: Optional[str] = None
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    status: str
    total_jobs_found: int
    jobs_created: int
    jobs_updated: int
    jobs_skipped: int
    jobs_failed: int
    error_count: int
    error_message: Optional[str]
    pages_crawled: Optional[int]
    avg_response_time_ms: Optional[float]
    success_rate: float
    crawler_version: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

class CrawlHistoryListResponse(BaseModel):
    data: List[CrawlHistoryResponse]
    total: int
    page: int
    limit: int
    max_page: int

class CrawlStatisticsResponse(BaseModel):
    period_days: int
    total_crawls: int
    successful_crawls: int
    failed_crawls: int
    running_crawls: int
    success_rate: float
    total_jobs_found: int
    total_jobs_created: int
    total_jobs_updated: int
    avg_duration_seconds: float
    last_crawl: Optional[str]

@router.get("/crawl-histories", response_model=CrawlHistoryListResponse)
async def get_crawl_histories(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    source_id: Optional[str] = Query(None, description="Filter by data source ID"),
    status: Optional[str] = Query("all", description="Filter by status"),
    sort_by: str = Query("started_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get paginated list of crawl histories"""
    
    # Check permissions
    if "crawl_history.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view crawl histories"
        )
    
    try:
        result = await CrawlHistoryService.get_crawl_histories(
            db=db,
            source_id=source_id,
            status=status,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return CrawlHistoryListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting crawl histories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/crawl-histories/{crawl_id}", response_model=CrawlHistoryResponse)
async def get_crawl_history(
    crawl_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get detailed crawl history by ID"""
    
    # Check permissions
    if "crawl_history.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view crawl history"
        )
    
    try:
        crawl_history = await CrawlHistoryService.get_crawl_history_by_id(db, crawl_id)
        
        if not crawl_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crawl history not found"
            )
        
        return CrawlHistoryResponse(**crawl_history)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting crawl history {crawl_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/data-sources/{source_id}/crawl-histories", response_model=CrawlHistoryListResponse)
async def get_crawl_histories_by_source(
    source_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query("all", description="Filter by status"),
    sort_by: str = Query("started_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get crawl histories for a specific data source"""
    
    # Check permissions
    if "crawl_history.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view crawl histories"
        )
    
    try:
        result = await CrawlHistoryService.get_crawl_histories(
            db=db,
            source_id=source_id,
            status=status,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return CrawlHistoryListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting crawl histories for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/crawl-statistics", response_model=CrawlStatisticsResponse)
async def get_crawl_statistics(
    source_id: Optional[str] = Query(None, description="Filter by data source ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get crawl statistics for the specified period"""
    
    # Check permissions
    if "crawl_history.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view crawl statistics"
        )
    
    try:
        stats = await CrawlHistoryService.get_crawl_statistics(
            db=db,
            source_id=source_id,
            days=days
        )
        
        return CrawlStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting crawl statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/crawl-histories/{crawl_id}/cancel")
async def cancel_crawl(
    crawl_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Cancel a running crawl"""
    
    # Check permissions
    if "crawl_history.cancel" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to cancel crawl"
        )
    
    try:
        crawl_history = await CrawlHistoryService.complete_crawl_session(
            db=db,
            crawl_id=crawl_id,
            status='cancelled',
            error_message="Cancelled by user"
        )
        
        if not crawl_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crawl history not found"
            )
        
        return {
            "message": "Crawl cancelled successfully",
            "crawl_id": crawl_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling crawl {crawl_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/data-sources/{source_id}/cancel-crawls")
async def cancel_source_crawls(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Cancel all running crawls for a data source"""
    
    # Check permissions
    if "crawl_history.cancel" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to cancel crawls"
        )
    
    try:
        cancelled_count = await CrawlHistoryService.cancel_running_crawls(
            db=db,
            source_id=source_id
        )
        
        return {
            "message": f"Cancelled {cancelled_count} running crawls",
            "source_id": source_id,
            "cancelled_count": cancelled_count
        }
        
    except Exception as e:
        logger.error(f"Error cancelling crawls for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )