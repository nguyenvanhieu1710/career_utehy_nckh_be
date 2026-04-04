"""
Job API endpoints using MongoDB (RESTful design)
Query from companies collection with nested jobs
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from app.services.job_mongo_service import job_mongo_service
from app.schemas.job_mongo import JobSearchSchema
import math
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def list_jobs(
    # Search parameters
    query: Optional[str] = Query(None, description="Search query for title/description"),
    location: Optional[str] = Query(None, description="Location filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    experience_level: Optional[str] = Query(None, description="Experience level filter"),
    company_id: Optional[str] = Query(None, description="Company ID filter"),
    salary_min: Optional[int] = Query(None, ge=0, description="Minimum salary"),
    salary_max: Optional[int] = Query(None, ge=0, description="Maximum salary"),
    remote_allowed: Optional[bool] = Query(None, description="Remote work allowed"),
    featured: Optional[bool] = Query(None, description="Featured jobs only"),
    
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    
    # Sorting
    sort_by: str = Query("created_at", description="Sort field (created_at, title, salary_min, salary_max)"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    List all jobs with optional filters and pagination
    
    GET /api/v1/job-mongo
    GET /api/v1/job-mongo?query=python&location=Hà Nội
    GET /api/v1/job-mongo?featured=true&limit=10
    GET /api/v1/job-mongo?page=2&limit=20
    """
    try:
        search_params = JobSearchSchema(
            query=query,
            location=location,
            job_type=job_type,
            experience_level=experience_level,
            company_id=company_id,
            salary_min=salary_min,
            salary_max=salary_max,
            remote_allowed=remote_allowed,
            featured=featured,
            status=None,
            page=page,
            size=limit,
            sort_by=sort_by,
            sort_order=order
        )
        
        jobs, total = await job_mongo_service.search_jobs(search_params)
        
        total_pages = math.ceil(total / limit) if total > 0 else 0
        
        return {
            "data": jobs,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )



@router.get("/stats")
async def get_statistics():
    """
    Get job statistics
    
    GET /api/v1/job-mongo/stats
    """
    try:
        stats = await job_mongo_service.get_job_stats()
        return {
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting job stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job statistics"
        )


@router.get("/{job_id}")
async def get_job(job_id: str):
    """
    Get a single job by ID
    
    GET /api/v1/job-mongo/{job_id}
    """
    job = await job_mongo_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id '{job_id}' not found"
        )
    
    return {
        "data": job
    }
