from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status
from app.models.job import Job
from app.models.company import Company
from app.schemas import get_schema
from app.core.perms import require_permission
from pydantic import BaseModel
from typing import Optional, List
import math
from datetime import datetime


# Pydantic models for API
class JobCreate(BaseModel):
    title: str
    company_id: str
    location: Optional[str] = None
    other_locations: Optional[List[str]] = None
    work_arrangement: Optional[str] = None
    job_type: str = "full-time"  # 'full-time', 'part-time', 'intern', 'freelance', 'contract'
    salary_display: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    skills: Optional[List[str]] = None
    requirements: Optional[str] = None
    description: Optional[str] = None
    benefits: Optional[str] = None
    status: str = "pending"  # 'pending', 'approved', 'rejected'
    source_id: Optional[str] = None
    url_source: Optional[str] = None
    posted_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company_id: Optional[str] = None
    location: Optional[str] = None
    other_locations: Optional[List[str]] = None
    work_arrangement: Optional[str] = None
    job_type: Optional[str] = None
    salary_display: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    skills: Optional[List[str]] = None
    requirements: Optional[str] = None
    description: Optional[str] = None
    benefits: Optional[str] = None
    status: Optional[str] = None
    source_id: Optional[str] = None
    url_source: Optional[str] = None
    posted_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


@require_permission(["job.create"])
async def create_job(user_perms: list[str], data: JobCreate, db: AsyncSession):
    """
    Create a new job
    """
    try:
        # Verify company exists
        company_result = await db.execute(select(Company).where(Company.id == data.company_id))
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company not found"
            )
        
        # Generate slug from title
        slug = data.title.lower().replace(" ", "-").replace("/", "-")
        
        # Check if slug already exists, if so append number
        base_slug = slug
        counter = 1
        while True:
            result = await db.execute(select(Job).where(Job.slug == slug))
            existing_job = result.scalar_one_or_none()
            if not existing_job:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create new job
        print(f"🔧 Creating job with data: title='{data.title}', company_id='{data.company_id}'")
        new_job = Job(
            title=data.title,
            slug=slug,
            company_id=data.company_id,
            location=data.location,
            other_locations=data.other_locations,
            work_arrangement=data.work_arrangement,
            job_type=data.job_type,
            salary_display=data.salary_display,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            skills=data.skills,
            requirements=data.requirements,
            description=data.description,
            benefits=data.benefits,
            status=data.status,
            source_id=data.source_id,
            url_source=data.url_source,
            posted_at=data.posted_at or datetime.utcnow(),
            expired_at=data.expired_at,
            action_status="active"
        )
        print(f"🔧 Job instance created: {new_job}")
        db.add(new_job)
        print("🔧 Job added to session, attempting commit...")
        await db.commit()
        print("🔧 Commit successful, refreshing...")
        await db.refresh(new_job)
        print(f"🔧 Job refreshed: {new_job.id}")
        
        return {
            "status": "success",
            "message": "Job created successfully",
            "data": new_job
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@require_permission(["job.list"])
async def get_all_jobs(user_perms: list[str], filters: get_schema.GetSchema, db: AsyncSession):
    """
    Get all jobs with pagination and search
    """
    base_stmt = select(Job).join(Company, Job.company_id == Company.id)
    
    # Filter out deleted jobs (soft delete) - allow NULL values for backward compatibility
    base_stmt = base_stmt.where((Job.action_status != "deleted") | (Job.action_status.is_(None)))

    if filters.id:
        base_stmt = base_stmt.where(Job.id == filters.id)

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            or_(
                Job.title.ilike(keyword),
                Job.location.ilike(keyword),
                Company.name.ilike(keyword),
                Job.description.ilike(keyword)
            )
        )

    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    
    # Count total records
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    # Get paginated data with company info
    result = await db.execute(base_stmt.offset(offset).limit(row))
    data = result.unique().scalars().all()

    max_page = math.ceil(total / row) if row > 0 else 1

    return {
        "total": total,
        "page": page,
        "max_page": max_page,
        "row": row,
        "data": data
    }


@require_permission(["job.read"])
async def get_job_by_id(user_perms: list[str], job_id: str, db: AsyncSession):
    """
    Get job by ID with company information
    """
    result = await db.execute(
        select(Job)
        .join(Company, Job.company_id == Company.id)
        .where(
            and_(
                Job.id == job_id,
                or_(Job.action_status != "deleted", Job.action_status.is_(None))
            )
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@require_permission(["job.update"])
async def update_job(user_perms: list[str], job_id: str, data: JobUpdate, db: AsyncSession):
    """
    Update job by ID
    """
    result = await db.execute(select(Job).where(
        and_(
            Job.id == job_id,
            or_(Job.action_status != "deleted", Job.action_status.is_(None))
        )
    ))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify company exists if company_id is being changed
    if data.company_id and data.company_id != job.company_id:
        company_result = await db.execute(select(Company).where(Company.id == data.company_id))
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company not found"
            )
    
    # Update fields
    update_fields = [
        "title", "company_id", "location", "other_locations", "work_arrangement",
        "job_type", "salary_display", "salary_min", "salary_max", "skills",
        "requirements", "description", "benefits", "status", "source_id",
        "url_source", "posted_at", "expired_at"
    ]
    
    for field in update_fields:
        value = getattr(data, field)
        if value is not None:
            setattr(job, field, value)
    
    # Update slug if title changed
    if data.title and data.title != job.title:
        slug = data.title.lower().replace(" ", "-").replace("/", "-")
        base_slug = slug
        counter = 1
        while True:
            check_result = await db.execute(select(Job).where(and_(Job.slug == slug, Job.id != job_id)))
            existing_job = check_result.scalar_one_or_none()
            if not existing_job:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        job.slug = slug

    await db.commit()
    await db.refresh(job)
    
    return {
        "status": "success",
        "message": "Job updated successfully",
        "data": job
    }


@require_permission(["job.delete"])
async def delete_job(user_perms: list[str], job_id: str, db: AsyncSession):
    """
    Soft delete job by ID
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Soft delete - change action_status to "deleted"
    job.action_status = "deleted"
    await db.commit()
    await db.refresh(job)
    
    return {
        "status": "success", 
        "message": "Job deleted successfully"
    }


@require_permission(["job.approve"])
async def approve_job(user_perms: list[str], job_id: str, db: AsyncSession):
    """
    Approve job (change status from pending to approved)
    """
    result = await db.execute(select(Job).where(
        and_(
            Job.id == job_id,
            or_(Job.action_status != "deleted", Job.action_status.is_(None))
        )
    ))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending jobs can be approved"
        )
    
    job.status = "approved"
    await db.commit()
    await db.refresh(job)
    
    return {
        "status": "success",
        "message": "Job approved successfully",
        "data": job
    }


@require_permission(["job.reject"])
async def reject_job(user_perms: list[str], job_id: str, db: AsyncSession):
    """
    Reject job (change status from pending to rejected)
    """
    result = await db.execute(select(Job).where(
        and_(
            Job.id == job_id,
            or_(Job.action_status != "deleted", Job.action_status.is_(None))
        )
    ))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending jobs can be rejected"
        )
    
    job.status = "rejected"
    await db.commit()
    await db.refresh(job)
    
    return {
        "status": "success",
        "message": "Job rejected successfully",
        "data": job
    }


@require_permission(["job.list"])
async def get_jobs_by_status(user_perms: list[str], job_status: str, filters: get_schema.GetSchema, db: AsyncSession):
    """
    Get jobs filtered by status (pending, approved, rejected)
    """
    base_stmt = select(Job).join(Company, Job.company_id == Company.id)
    
    # Filter by status and exclude deleted
    base_stmt = base_stmt.where(
        and_(
            Job.status == job_status,
            or_(Job.action_status != "deleted", Job.action_status.is_(None))
        )
    )

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            or_(
                Job.title.ilike(keyword),
                Job.location.ilike(keyword),
                Company.name.ilike(keyword)
            )
        )

    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    
    # Count total records
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    # Get paginated data
    result = await db.execute(base_stmt.offset(offset).limit(row))
    data = result.unique().scalars().all()

    max_page = math.ceil(total / row) if row > 0 else 1

    return {
        "total": total,
        "page": page,
        "max_page": max_page,
        "row": row,
        "data": data
    }