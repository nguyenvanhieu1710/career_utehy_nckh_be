from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from app.models import cv_profile
from app.models import perm_groups
from app.schemas import get_schema
from passlib.context import CryptContext
from app.utils import auth
from sqlalchemy.exc import IntegrityError
import string
import secrets
import math

from app.models import cv_template


async def create_cv(
    data: cv_profile.CVSave,
    user_id: str,
    db: AsyncSession
):
    if not data.template_id:
        templates = await db.execute(select(cv_template.CVTemplate).limit(1))
        template = templates.scalar_one_or_none()
    else:
        result = await db.execute(select(cv_template.CVTemplate).where(cv_template.CVTemplate.id == data.template_id))
        template = result.scalar_one_or_none()
    new_item = cv_profile.CVProfile(
        name="New CV",
        user_id=user_id,
        title=data.title,
        subtitle=data.subtitle,
        primary_color=data.primary_color,
        sections=data.sections,
        design_data=template.design_data if template else None,
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item

async def update_cv(
    data: cv_profile.CVSave,
    user_id: str,
    db: AsyncSession
):
    result = await db.execute(
        select(cv_profile.CVProfile).where(cv_profile.CVProfile.id == data.id).where(cv_profile.CVProfile.user_id == user_id)
    )
    cv = result.scalar_one_or_none()

    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(cv, key, value)

    await db.commit()
    await db.refresh(cv)
    return cv

async def cv_save(
    data: cv_profile.CVSave,
    user_id: str,
    db: AsyncSession
):
    if not data.id:
        return await create_cv(data, user_id, db)
    return await update_cv(data, user_id, db)

async def get_cv_for_user(user_id: str, filters: get_schema.GetSchema, db: AsyncSession):
    base_stmt = select(cv_profile.CVProfile).where(cv_profile.CVProfile.user_id == user_id)

    if filters.id:
        base_stmt = base_stmt.where(cv_profile.CVProfile.id == filters.id)

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            (cv_profile.CVProfile.title.ilike(keyword)) |
            (cv_profile.CVProfile.name.ilike(keyword))
        )

    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
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