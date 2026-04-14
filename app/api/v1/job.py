from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import job_service, user_service, company_service, import_job_service
from app.services.job_service import JobCreate, JobUpdate
from app.schemas import get_schema
from app.utils import auth

from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

class MinioImportRequest(BaseModel):
    bucket: str
    object_name: str

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/get-jobs")
async def get_jobs(
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all jobs with pagination and search
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.get_all_jobs(user_perms=perms, filters=filters, db=db)
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


@router.get("/get-job/{job_id}")
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get job by ID with company information
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.get_job_by_id(user_perms=perms, job_id=job_id, db=db)
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


@router.post("/create-job")
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Create a new job
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.create_job(user_perms=perms, data=data, db=db)
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


@router.put("/update-job/{job_id}")
async def update_job(
    job_id: str,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Update job by ID
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.update_job(user_perms=perms, job_id=job_id, data=data, db=db)
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


@router.delete("/delete-job/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Delete job by ID (soft delete)
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.delete_job(user_perms=perms, job_id=job_id, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/approve-job/{job_id}")
async def approve_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Approve job (change status from pending to approved)
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.approve_job(user_perms=perms, job_id=job_id, db=db)
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


@router.put("/reject-job/{job_id}")
async def reject_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Reject job (change status from pending to rejected)
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.reject_job(user_perms=perms, job_id=job_id, db=db)
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


@router.post("/get-jobs-by-status/{job_status}")
async def get_jobs_by_status(
    job_status: str,
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get jobs filtered by status (pending, approved, rejected)
    """
    try:
        # Validate status
        valid_statuses = ["pending", "approved", "rejected"]
        if job_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await job_service.get_jobs_by_status(
            user_perms=perms, 
            job_status=job_status, 
            filters=filters, 
            db=db
        )
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


# Company endpoints for job management
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

@router.post("/import-minio")
async def import_from_minio(
    data: MinioImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Import jobs directly from MinIO via SDK
    """
    try:
        result = await import_job_service.ImportJobService.import_from_minio(
            db=db, 
            bucket=data.bucket, 
            object_name=data.object_name
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
