from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from app.models.company import Company
from app.schemas import get_schema
from app.core.perms import require_permission
from pydantic import BaseModel
from typing import Optional, List
import math


# Pydantic models for API
class CompanyCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    sub_industries: Optional[List[str]] = None
    size: Optional[str] = None
    locations: Optional[List[str]] = None
    email: Optional[str] = None
    support_email: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    sub_industries: Optional[List[str]] = None
    size: Optional[str] = None
    locations: Optional[List[str]] = None
    email: Optional[str] = None
    support_email: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True


@require_permission(["company.list"])
async def get_all_companies(user_perms: list[str], filters: get_schema.GetSchema, db: AsyncSession):
    """
    Get all companies with pagination and search
    """
    base_stmt = select(Company)
    
    # Filter out deleted companies (soft delete) - allow NULL values for backward compatibility
    base_stmt = base_stmt.where((Company.action_status != "deleted") | (Company.action_status.is_(None)))

    if filters.id:
        base_stmt = base_stmt.where(Company.id == filters.id)

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            or_(
                Company.name.ilike(keyword),
                Company.industry.ilike(keyword),
                Company.address.ilike(keyword)
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


@require_permission(["company.list"])
async def get_companies_for_dropdown(user_perms: list[str], db: AsyncSession):
    """
    Get simplified list of companies for dropdown/select options
    """
    result = await db.execute(
        select(Company.id, Company.name)
        .where((Company.action_status != "deleted") | (Company.action_status.is_(None)))
        .order_by(Company.name)
    )
    companies = result.all()
    
    return [
        {"id": str(company.id), "name": company.name}
        for company in companies
    ]


@require_permission(["company.read"])
async def get_company_by_id(user_perms: list[str], company_id: str, db: AsyncSession):
    """
    Get company by ID
    """
    result = await db.execute(select(Company).where(
        (Company.id == company_id) & 
        ((Company.action_status != "deleted") | (Company.action_status.is_(None)))
    ))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return company


@require_permission(["company.create"])
async def create_company(user_perms: list[str], data: CompanyCreate, db: AsyncSession):
    """
    Create a new company
    """
    try:
        # Generate slug from name if not provided
        if not data.slug:
            slug = data.name.lower().replace(" ", "-").replace("/", "-")
        else:
            slug = data.slug
        
        # Check if slug already exists
        result = await db.execute(select(Company).where(Company.slug == slug))
        existing_company = result.scalar_one_or_none()
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company slug already exists"
            )
        
        # Create new company
        new_company = Company(
            name=data.name,
            slug=slug,
            logo_url=data.logo_url,
            website=data.website,
            address=data.address,
            description=data.description,
            industry=data.industry,
            sub_industries=data.sub_industries,
            size=data.size,
            locations=data.locations,
            email=data.email,
            support_email=data.support_email,
            phone=data.phone,
            action_status="active"
        )
        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)
        
        return {
            "status": "success",
            "message": "Company created successfully",
            "data": new_company
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@require_permission(["company.update"])
async def update_company(user_perms: list[str], company_id: str, data: CompanyUpdate, db: AsyncSession):
    """
    Update company by ID
    """
    result = await db.execute(select(Company).where(
        (Company.id == company_id) & 
        ((Company.action_status != "deleted") | (Company.action_status.is_(None)))
    ))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if new slug already exists (if slug is being changed)
    if data.slug and data.slug != company.slug:
        check_result = await db.execute(select(Company).where(Company.slug == data.slug))
        existing_company = check_result.scalar_one_or_none()
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company slug already exists"
            )
    
    # Update fields
    update_fields = [
        "name", "slug", "logo_url", "website", "address", "description",
        "industry", "sub_industries", "size", "locations", "email",
        "support_email", "phone"
    ]
    
    for field in update_fields:
        value = getattr(data, field)
        if value is not None:
            setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    
    return {
        "status": "success",
        "message": "Company updated successfully",
        "data": company
    }


@require_permission(["company.delete"])
async def delete_company(user_perms: list[str], company_id: str, db: AsyncSession):
    """
    Soft delete company by ID
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if company has active jobs
    from app.models.job import Job
    jobs_result = await db.execute(
        select(func.count(Job.id))
        .where(
            (Job.company_id == company_id) & 
            ((Job.action_status != "deleted") | (Job.action_status.is_(None)))
        )
    )
    active_jobs_count = jobs_result.scalar()
    
    if active_jobs_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete company with {active_jobs_count} active jobs"
        )
    
    # Soft delete - change action_status to "deleted"
    company.action_status = "deleted"
    await db.commit()
    await db.refresh(company)
    
    return {
        "status": "success", 
        "message": "Company deleted successfully"
    }