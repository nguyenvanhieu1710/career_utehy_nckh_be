"""
Job API endpoints using MongoDB
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from app.schemas.job_mongo import (
    JobCreateSchema, 
    JobUpdateSchema, 
    JobResponseSchema, 
    JobListResponseSchema,
    JobSearchSchema,
    JobStatsSchema
)
from app.services.job_mongo_service import job_mongo_service
from app.models.mongo.job import JobStatus, JobType, ExperienceLevel
from app.utils import auth
from app.models.user import Users
import math
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=JobResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreateSchema,
    user_id: str = Depends(auth.verify_token_user)
):
    """Create a new job posting"""
    try:
        job = await job_mongo_service.create_job(job_data)
        return JobResponseSchema(
            id=str(job.id),
            **job.dict()
        )
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )

@router.get("/{job_id}", response_model=JobResponseSchema)
async def get_job(job_id: str):
    """Get job by ID"""
    job = await job_mongo_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponseSchema(
        id=str(job.id),
        **job.dict()
    )

@router.put("/{job_id}", response_model=JobResponseSchema)
async def update_job(
    job_id: str,
    job_data: JobUpdateSchema,
    user_id: str = Depends(auth.verify_token_user)
):
    """Update job"""
    try:
        job = await job_mongo_service.update_job(job_id, job_data)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobResponseSchema(
            id=str(job.id),
            **job.dict()
        )
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job"
        )

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    user_id: str = Depends(auth.verify_token_user)
):
    """Delete job"""
    try:
        success = await job_mongo_service.delete_job(job_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job"
        )

@router.get("/", response_model=JobListResponseSchema)
async def search_jobs(
    # Search parameters
    query: Optional[str] = Query(None, description="Search query for title/description"),
    location: Optional[str] = Query(None, description="Location filter"),
    job_type: Optional[JobType] = Query(None, description="Job type filter"),
    experience_level: Optional[ExperienceLevel] = Query(None, description="Experience level filter"),
    company_id: Optional[str] = Query(None, description="Company ID filter"),
    category_ids: Optional[List[str]] = Query(None, description="Category IDs filter"),
    salary_min: Optional[int] = Query(None, ge=0, description="Minimum salary"),
    salary_max: Optional[int] = Query(None, ge=0, description="Maximum salary"),
    remote_allowed: Optional[bool] = Query(None, description="Remote work allowed"),
    featured: Optional[bool] = Query(None, description="Featured jobs only"),
    status: Optional[JobStatus] = Query(JobStatus.ACTIVE, description="Job status"),
    
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    
    # Sorting
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """Search jobs with filters and pagination"""
    try:
        search_params = JobSearchSchema(
            query=query,
            location=location,
            job_type=job_type,
            experience_level=experience_level,
            company_id=company_id,
            category_ids=category_ids,
            salary_min=salary_min,
            salary_max=salary_max,
            remote_allowed=remote_allowed,
            featured=featured,
            status=status,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        jobs, total = await job_mongo_service.search_jobs(search_params)
        
        job_responses = [
            JobResponseSchema(id=str(job.id), **job.dict())
            for job in jobs
        ]
        
        total_pages = math.ceil(total / size) if total > 0 else 0
        
        return JobListResponseSchema(
            jobs=job_responses,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search jobs"
        )

@router.get("/company/{company_id}", response_model=List[JobResponseSchema])
async def get_jobs_by_company(
    company_id: str,
    status: Optional[JobStatus] = Query(JobStatus.ACTIVE, description="Job status"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of jobs")
):
    """Get jobs by company"""
    try:
        jobs = await job_mongo_service.get_jobs_by_company(company_id, status, limit)
        return [
            JobResponseSchema(id=str(job.id), **job.dict())
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error getting jobs for company {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get company jobs"
        )

@router.get("/featured/list", response_model=List[JobResponseSchema])
async def get_featured_jobs(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of jobs")
):
    """Get featured jobs"""
    try:
        jobs = await job_mongo_service.get_featured_jobs(limit)
        return [
            JobResponseSchema(id=str(job.id), **job.dict())
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error getting featured jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get featured jobs"
        )

@router.get("/recent/list", response_model=List[JobResponseSchema])
async def get_recent_jobs(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of jobs")
):
    """Get recent jobs"""
    try:
        jobs = await job_mongo_service.get_recent_jobs(limit)
        return [
            JobResponseSchema(id=str(job.id), **job.dict())
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error getting recent jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent jobs"
        )

@router.post("/{job_id}/view", status_code=status.HTTP_200_OK)
async def increment_job_views(job_id: str):
    """Increment job view count"""
    try:
        success = await job_mongo_service.increment_job_views(job_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return {"message": "View count incremented"}
    except Exception as e:
        logger.error(f"Error incrementing views for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to increment view count"
        )

@router.post("/{job_id}/apply", status_code=status.HTTP_200_OK)
async def increment_job_applications(job_id: str):
    """Increment job application count"""
    try:
        success = await job_mongo_service.increment_job_applications(job_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return {"message": "Application count incremented"}
    except Exception as e:
        logger.error(f"Error incrementing applications for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to increment application count"
        )

@router.get("/stats/overview", response_model=JobStatsSchema)
async def get_job_stats(user_id: str = Depends(auth.verify_token_user)):
    """Get job statistics (admin only)"""
    try:
        stats = await job_mongo_service.get_job_stats()
        return JobStatsSchema(**stats)
    except Exception as e:
        logger.error(f"Error getting job stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job statistics"
        )