
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, status
from app.services import user_service, roles_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.models import perm_groups
from app.schemas import get_schema
from sqlalchemy.dialects.postgresql import UUID
import uuid
import json
from app.utils import auth
from app.core import perms
router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/get-perms")
async def blog_get():
    return perms.get_all_permissions()


@router.post("/create")
async def create(data: perm_groups.CreateGroup, db: AsyncSession = Depends(get_db), user_id: str = Depends(auth.verify_token_user)):
    perms = await user_service.get_user_permissions(user_id=user_id, db=db)
    res = await roles_service.create(user_perms=perms, data=data, db=db)
    return res

@router.put("/update/{id}")
async def create(id:str, data: perm_groups.CreateGroup, db: AsyncSession = Depends(get_db), user_id: str = Depends(auth.verify_token_user)):
    perms = await user_service.get_user_permissions(user_id=user_id, db=db)
    res = await roles_service.update(user_perms=perms, group_id=id, data=data, db=db)
    return res

@router.delete("/delete/{id}")
async def create(id:str, db: AsyncSession = Depends(get_db), user_id: str = Depends(auth.verify_token_user)):
    perms = await user_service.get_user_permissions(user_id=user_id, db=db)
    res = await roles_service.delete_group(user_perms=perms, id=id, db=db)
    return res

@router.post("/get-roles")
async def get_roles(
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await roles_service.get(filters=filters, db=db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    