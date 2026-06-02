from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, Form, status
from app.services import cv_service, matching_proxy_service
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.models import cv_profile
from sqlalchemy.dialects.postgresql import UUID
import uuid
import json
from app.utils import auth
from app.core.perms import require_permission

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/create")
async def cv_create(
        data: cv_profile.CVSave,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    result = await cv_service.create_cv(data=data,user_id=user_id, db=db)
    return result

@router.post("/update")
async def cv_update(
        data: cv_profile.CVSave,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    result = await cv_service.update_cv(data=data,user_id=user_id, db=db)
    return result

@router.post("/get-for-user")
async def get(
        filters: get_schema.GetSchema,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    result = await cv_service.get_cv_for_user(user_id=user_id,filters=filters, db=db)
    return result

@router.delete("/{cv_id}")
async def cv_delete(
        cv_id: str,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    result = await cv_service.delete_cv(cv_id=cv_id, user_id=user_id, db=db)
    return result

@router.put("/{cv_id}/set-primary")
async def cv_set_primary(
        cv_id: str,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """Set a CV Online as the primary CV for matching"""
    return await cv_service.set_primary_cv(cv_id=cv_id, user_id=user_id, cv_type="profile", db=db)

@router.put("/{cv_id}/unset-primary")
async def cv_unset_primary(
        cv_id: str,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """Unset a CV Online as the primary CV"""
    return await cv_service.unset_primary_cv(cv_id=cv_id, user_id=user_id, cv_type="profile", db=db)

@router.get("/recommendations/{cv_id}")
async def get_recommendations(
        cv_id: str,
        top_k: int = Query(10, ge=1, le=50),
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """
    Get job recommendations based on a specific Online CV profile (Scenario 2)
    """
    return await matching_proxy_service.MatchingProxyService.get_recommendations(
        cv_id=cv_id,
        user_id=user_id,
        db=db,
        top_k=top_k
    )

@router.get("/recommendations/file/{cv_id}")
async def get_recommendations_from_file(
        cv_id: str,
        top_k: int = Query(10, ge=1, le=50),
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """
    Get job recommendations based on a specific Uploaded PDF CV (Scenario 3)
    """
    return await matching_proxy_service.MatchingProxyService.get_recommendations_from_file(
        cv_id=cv_id,
        user_id=user_id,
        db=db,
        top_k=top_k
    )

@router.get("/recommendations-auto")
async def get_recommendations_auto(
        top_k: int = Query(10, ge=1, le=50),
        source: Optional[str] = Query(None, description="Source of CV: 'profile', 'file', or 'auto'"),
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """
    Automatically detect or use specific CV source for recommendations
    """
    return await matching_proxy_service.MatchingProxyService.get_auto_recommendations(
        user_id=user_id,
        db=db,
        top_k=top_k,
        source=source
    )
