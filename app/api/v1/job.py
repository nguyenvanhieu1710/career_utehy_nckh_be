from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import job_service, user_service, company_service
from app.services.job_service import JobCreate, JobUpdate
from app.schemas import get_schema
from app.utils import auth

router = APIRouter()

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
        print("=" * 60)
        print("📥 GET JOBS REQUEST")
        print(f"User ID: {user_id}")
        print(f"Filters: {filters}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.get_all_jobs(user_perms=perms, filters=filters, db=db)
        print(f"✅ Success: Found {result.get('total', 0)} jobs")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print("📥 CREATE JOB REQUEST")
        print(f"User ID: {user_id}")
        print(f"Job data: title='{data.title}', company_id='{data.company_id}'")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.create_job(user_perms=perms, data=data, db=db)
        print(f"✅ Success: Job created with ID {result['data'].id}")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print("📥 UPDATE JOB REQUEST")
        print(f"User ID: {user_id}")
        print(f"Job ID: {job_id}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.update_job(user_perms=perms, job_id=job_id, data=data, db=db)
        print(f"✅ Success: Job updated")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print("📥 DELETE JOB REQUEST")
        print(f"User ID: {user_id}")
        print(f"Job ID: {job_id}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.delete_job(user_perms=perms, job_id=job_id, db=db)
        print(f"✅ Success: Job deleted")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
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
        print("=" * 60)
        print("📥 APPROVE JOB REQUEST")
        print(f"User ID: {user_id}")
        print(f"Job ID: {job_id}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.approve_job(user_perms=perms, job_id=job_id, db=db)
        print(f"✅ Success: Job approved")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print("📥 REJECT JOB REQUEST")
        print(f"User ID: {user_id}")
        print(f"Job ID: {job_id}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.reject_job(user_perms=perms, job_id=job_id, db=db)
        print(f"✅ Success: Job rejected")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print(f"📥 GET JOBS BY STATUS REQUEST: {job_status}")
        print(f"User ID: {user_id}")
        print(f"Filters: {filters}")
        
        # Validate status
        valid_statuses = ["pending", "approved", "rejected"]
        if job_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await job_service.get_jobs_by_status(
            user_perms=perms, 
            job_status=job_status, 
            filters=filters, 
            db=db
        )
        print(f"✅ Success: Found {result.get('total', 0)} {job_status} jobs")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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