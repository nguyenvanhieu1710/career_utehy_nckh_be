from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, Form, status
from app.services import cv_service
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
