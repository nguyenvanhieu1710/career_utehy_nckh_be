from fastapi import APIRouter, UploadFile, Depends, Form
from app.services import cv_uploaded_service
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.utils import auth

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/upload")
async def upload_cv(
    file: UploadFile,
    name: str = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Endpoint to upload a PDF CV
    """
    result = await cv_uploaded_service.upload_cv(
        file=file,
        name=name,
        user_id=user_id,
        db=db
    )
    return result

@router.post("/get-for-user")
async def get_uploaded_cvs(
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Endpoint to list user's uploaded CVs
    """
    result = await cv_uploaded_service.get_uploaded_cvs(
        user_id=user_id,
        filters=filters,
        db=db
    )
    return result

@router.delete("/{cv_id}")
async def delete_uploaded_cv(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Endpoint to delete an uploaded CV
    """
    result = await cv_uploaded_service.delete_uploaded_cv(
        cv_id=cv_id,
        user_id=user_id,
        db=db
    )
    return result

@router.put("/{cv_id}/set-primary")
async def set_uploaded_cv_primary(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """Set an uploaded PDF CV as the primary CV for matching"""
    from app.services import cv_service
    return await cv_service.set_primary_cv(cv_id=cv_id, user_id=user_id, cv_type="uploaded", db=db)

@router.put("/{cv_id}/unset-primary")
async def unset_uploaded_cv_primary(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """Unset an uploaded PDF CV as the primary CV"""
    from app.services import cv_service
    return await cv_service.unset_primary_cv(cv_id=cv_id, user_id=user_id, cv_type="uploaded", db=db)
