from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import company_service, user_service
from app.services.company_service import CompanyCreate, CompanyUpdate
from app.schemas import get_schema
from app.utils import auth

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/get-companies")
async def get_companies(
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all companies with pagination and search
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.get_all_companies(user_perms=perms, filters=filters, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/get-companies-dropdown")
async def get_companies_dropdown(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get simplified list of companies for dropdown/select options
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.get_companies_for_dropdown(user_perms=perms, db=db)
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/get-company/{company_id}")
async def get_company_detail(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get company by ID
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.get_company_by_id(user_perms=perms, company_id=company_id, db=db)
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/create-company")
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Create a new company
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.create_company(user_perms=perms, data=data, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/update-company/{company_id}")
async def update_company(
    company_id: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Update company by ID
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.update_company(user_perms=perms, company_id=company_id, data=data, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/delete-company/{company_id}")
async def delete_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Delete company by ID (soft delete)
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await company_service.delete_company(user_perms=perms, company_id=company_id, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# RESTful endpoint for company jobs (MongoDB)
@router.get("/{company_id}/jobs")
async def get_company_jobs(
    company_id: str,
    status: str = None,
    limit: int = 10
):
    """
    Get jobs for a specific company (RESTful endpoint)
    
    GET /api/v1/company/{company_id}/jobs
    GET /api/v1/company/{company_id}/jobs?status=active&limit=20
    """
    from app.services.job_mongo_service import job_mongo_service
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        jobs = await job_mongo_service.get_jobs_by_company(company_id, status, limit)
        return {
            "data": jobs,
            "total": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error getting jobs for company {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get company jobs"
        )
