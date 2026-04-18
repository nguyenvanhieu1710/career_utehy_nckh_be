from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.core.database import SessionLocal
from app.services import category_service
from app.core.status import EntityStatus
from app.models.user import Users
from app.models.job import Job
from app.models.company import Company

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.get("/categories")
async def get_public_categories(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get active categories for public display (no authentication required)
    
    - **limit**: Maximum number of categories to return (default: 20, max: 50)
    
    Returns only active categories with basic information
    """
    try:
        # Validate limit
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 20
        
        # Get active categories without permission check
        result = await category_service.get_public_categories(limit=limit, db=db)
        
        return {
            "status": "success",
            "data": result,
            "total": len(result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch public categories"
        )


@router.get("/categories/{category_id}")
async def get_public_category_detail(
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get public category detail by ID (no authentication required)
    
    - **category_id**: ID of the category
    
    Returns category details if active
    """
    try:
        # Get category detail without permission check
        result = await category_service.get_public_category_by_id(category_id=category_id, db=db)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or not active"
            )
        
        return {
            "status": "success",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch category details"
        )


@router.get("/stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """
    Get public statistics for the hero section (no authentication required).

    Returns:
    - **user_count**: Total number of registered users
    - **job_count**: Total number of approved jobs
    - **company_count**: Total number of active companies
    """
    try:
        # Count all users
        user_result = await db.execute(select(func.count()).select_from(Users))
        user_count = user_result.scalar() or 0

        # Count approved jobs
        job_result = await db.execute(
            select(func.count()).select_from(Job).where(Job.status == "approved")
        )
        job_count = job_result.scalar() or 0

        # Count active companies
        company_result = await db.execute(
            select(func.count()).select_from(Company).where(Company.action_status == "active")
        )
        company_count = company_result.scalar() or 0

        return {
            "status": "success",
            "data": {
                "user_count": user_count,
                "job_count": job_count,
                "company_count": company_count,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )