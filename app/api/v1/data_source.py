from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.services.data_source_service import DataSourceService
from app.utils.auth import get_current_user_permissions
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Data source name")
    base_url: Optional[str] = Field(None, max_length=255, description="Base URL for the data source")
    status: Optional[str] = Field("inactive", pattern="^(active|inactive)$", description="Status of the data source")
    # Crawl config fields
    crawl_frequency: Optional[str] = Field("daily", pattern="^(hourly|daily|weekly)$", description="Crawl frequency")
    crawl_enabled: Optional[bool] = Field(True, description="Enable/disable crawling")

class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Data source name")
    base_url: Optional[str] = Field(None, max_length=255, description="Base URL for the data source")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$", description="Status of the data source")
    # Crawl config fields
    crawl_frequency: Optional[str] = Field(None, pattern="^(hourly|daily|weekly)$", description="Crawl frequency")
    crawl_enabled: Optional[bool] = Field(None, description="Enable/disable crawling")

class DataSourceResponse(BaseModel):
    id: str
    name: str
    base_url: Optional[str]
    status: str
    last_crawled_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    total_records: int
    recent_records: int
    success_rate: float
    # Crawler config info
    crawl_frequency: str
    crawl_enabled: bool
    next_run_at: Optional[str]

class DataSourceListResponse(BaseModel):
    data: List[DataSourceResponse]
    total: int
    page: int
    limit: int
    max_page: int

@router.get("/data-sources", response_model=DataSourceListResponse)
async def get_data_sources(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search_keyword: Optional[str] = Query(None, description="Search keyword"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get paginated list of data sources"""
    
    # Check permissions
    if "data_source.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view data sources"
        )
    
    try:
        result = await DataSourceService.get_data_sources(
            db=db,
            page=page,
            limit=limit,
            search_keyword=search_keyword,
            status=status_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return DataSourceListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting data sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/data-sources/{data_source_id}", response_model=DataSourceResponse)
async def get_data_source(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get data source by ID"""
    
    # Check permissions
    if "data_source.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view data source"
        )
    
    try:
        data_source = await DataSourceService.get_data_source_by_id(db, data_source_id)
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source not found"
            )
        
        # Get statistics
        stats = await DataSourceService.get_data_source_statistics(db, data_source_id)
        
        # Get crawler config info
        from app.services.crawler_config_service import CrawlerConfigService
        crawler_config = await CrawlerConfigService.get_config_by_source_id(db, data_source_id)
        
        # Get next scheduled crawl
        from app.services.crawl_history_service import CrawlHistoryService
        next_run_at = await CrawlHistoryService.get_next_scheduled_crawl(db, data_source_id)
        
        return DataSourceResponse(
            id=str(data_source.id),
            name=data_source.name,
            base_url=data_source.base_url,
            status=data_source.status,
            last_crawled_at=data_source.last_crawled_at.isoformat() if data_source.last_crawled_at else None,
            created_at=data_source.created_at.isoformat() if data_source.created_at else None,
            updated_at=data_source.updated_at.isoformat() if data_source.updated_at else None,
            total_records=stats.get("total_jobs", 0),
            recent_records=stats.get("jobs_last_30_days", 0),
            success_rate=stats.get("success_rate", 0.0),
            # Crawler config info
            crawl_frequency=crawler_config.frequency if crawler_config else "daily",
            crawl_enabled=crawler_config.status == "enabled" if crawler_config else False,
            next_run_at=next_run_at.isoformat() if next_run_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source {data_source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/data-sources", response_model=DataSourceResponse)
async def create_data_source(
    data_source_data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Create new data source"""
    
    # Check permissions
    if "data_source.create" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create data source"
        )
    
    try:
        # Check if data source with same name exists
        from app.models.data_source import DataSource as DataSourceModel
        from sqlalchemy import select
        
        result = await db.execute(select(DataSourceModel).filter(DataSourceModel.name == data_source_data.name))
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data source with this name already exists"
            )
        
        data_source = await DataSourceService.create_data_source(
            db=db,
            name=data_source_data.name,
            base_url=data_source_data.base_url,
            status=data_source_data.status or "inactive",
            crawl_frequency=data_source_data.crawl_frequency or "daily",
            crawl_enabled=data_source_data.crawl_enabled if data_source_data.crawl_enabled is not None else True
        )
        
        return DataSourceResponse(
            id=str(data_source.id),
            name=data_source.name,
            base_url=data_source.base_url,
            status=data_source.status,
            last_crawled_at=data_source.last_crawled_at.isoformat() if data_source.last_crawled_at else None,
            created_at=data_source.created_at.isoformat() if data_source.created_at else None,
            updated_at=data_source.updated_at.isoformat() if data_source.updated_at else None,
            total_records=0,
            recent_records=0,
            success_rate=0.0,
            # Crawler config info
            crawl_frequency=data_source_data.crawl_frequency or "daily",
            crawl_enabled=data_source_data.crawl_enabled if data_source_data.crawl_enabled is not None else True,
            next_run_at=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/data-sources/{data_source_id}", response_model=DataSourceResponse)
async def update_data_source(
    data_source_id: str,
    data_source_data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Update data source"""
    
    # Check permissions
    if "data_source.update" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update data source"
        )
    
    try:
        data_source = await DataSourceService.update_data_source(
            db=db,
            data_source_id=data_source_id,
            name=data_source_data.name,
            base_url=data_source_data.base_url,
            status=data_source_data.status,
            crawl_frequency=data_source_data.crawl_frequency,
            crawl_enabled=data_source_data.crawl_enabled
        )
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source not found"
            )
        
        # Get updated statistics
        stats = await DataSourceService.get_data_source_statistics(db, data_source_id)
        
        # Get updated crawler config info
        from app.services.crawler_config_service import CrawlerConfigService
        crawler_config = await CrawlerConfigService.get_config_by_source_id(db, data_source_id)
        
        # Get next scheduled crawl
        from app.services.crawl_history_service import CrawlHistoryService
        next_run_at = await CrawlHistoryService.get_next_scheduled_crawl(db, data_source_id)
        
        return DataSourceResponse(
            id=str(data_source.id),
            name=data_source.name,
            base_url=data_source.base_url,
            status=data_source.status,
            last_crawled_at=data_source.last_crawled_at.isoformat() if data_source.last_crawled_at else None,
            created_at=data_source.created_at.isoformat() if data_source.created_at else None,
            updated_at=data_source.updated_at.isoformat() if data_source.updated_at else None,
            total_records=stats.get("total_jobs", 0),
            recent_records=stats.get("jobs_last_30_days", 0),
            success_rate=stats.get("success_rate", 0.0),
            # Crawler config info
            crawl_frequency=crawler_config.frequency if crawler_config else "daily",
            crawl_enabled=crawler_config.status == "enabled" if crawler_config else False,
            next_run_at=next_run_at.isoformat() if next_run_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data source {data_source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/data-sources/{data_source_id}")
async def delete_data_source(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Delete data source"""
    
    # Check permissions
    if "data_source.delete" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete data source"
        )
    
    try:
        success = await DataSourceService.delete_data_source(db, data_source_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source not found"
            )
        
        return {"message": "Data source deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data source {data_source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/data-sources/{data_source_id}/statistics")
async def get_data_source_statistics(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Get detailed statistics for a data source"""
    
    # Check permissions
    if "data_source.view" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view data source statistics"
        )
    
    try:
        stats = await DataSourceService.get_data_source_statistics(db, data_source_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source not found"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics for data source {data_source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/data-sources/{data_source_id}/crawl")
async def trigger_crawl(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    permissions: List[str] = Depends(get_current_user_permissions)
):
    """Trigger manual crawl for a data source"""
    
    # Check permissions
    if "data_source.crawl" not in permissions and "*" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to trigger crawl"
        )
    
    try:
        data_source = await DataSourceService.get_data_source_by_id(db, data_source_id)
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data source not found"
            )
        
        # Update last crawled timestamp
        await DataSourceService.update_last_crawled(db, data_source_id)
        
        # TODO: Implement actual crawling logic here
        # For now, just return success message
        
        return {
            "message": "Crawl triggered successfully",
            "data_source_id": data_source_id,
            "status": "started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering crawl for data source {data_source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )