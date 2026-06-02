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
        title=data.title if data.title is not None else (template.default_title if template else None),
        subtitle=data.subtitle if data.subtitle is not None else (template.default_subtitle if template else None),
        primary_color=data.primary_color if data.primary_color is not None else (template.primary_color if template else None),
        sections=data.sections if data.sections is not None else (template.default_sections if template else None),
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

async def delete_cv(cv_id: str, user_id: str, db: AsyncSession):
    result = await db.execute(
        select(cv_profile.CVProfile).where(cv_profile.CVProfile.id == cv_id).where(cv_profile.CVProfile.user_id == user_id)
    )
    cv = result.scalar_one_or_none()

    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found or you do not have permission to delete it"
        )

    await db.delete(cv)
    await db.commit()
    return {"status": "success", "message": "CV deleted successfully"}

async def set_primary_cv(cv_id: str, user_id: str, cv_type: str, db: AsyncSession):
    """
    Set a CV as primary. Clears is_primary on ALL user CVs (both tables), then marks the chosen one.
    cv_type: 'profile' or 'uploaded'
    """
    from app.models.cv_uploaded import CVUploaded
    from sqlalchemy import update

    # 1. Clear all is_primary for this user on the relevant table
    if cv_type == "profile":
        await db.execute(
            update(cv_profile.CVProfile)
            .where(cv_profile.CVProfile.user_id == user_id)
            .values(is_primary=False)
        )
    elif cv_type == "uploaded":
        await db.execute(
            update(CVUploaded)
            .where(CVUploaded.user_id == user_id)
            .values(is_primary=False)
        )

    # 2. Set the chosen CV as primary
    if cv_type == "profile":
        result = await db.execute(
            select(cv_profile.CVProfile)
            .where(cv_profile.CVProfile.id == cv_id, cv_profile.CVProfile.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
        if not cv:
            raise HTTPException(status_code=404, detail="CV not found")
        cv.is_primary = True
    elif cv_type == "uploaded":
        result = await db.execute(
            select(CVUploaded)
            .where(CVUploaded.id == cv_id, CVUploaded.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
        if not cv:
            raise HTTPException(status_code=404, detail="Uploaded CV not found")
        cv.is_primary = True
    else:
        raise HTTPException(status_code=400, detail="Invalid cv_type, must be 'profile' or 'uploaded'")

    await db.commit()
    return {"status": "success", "message": "CV đã được đặt làm CV chính"}

async def unset_primary_cv(cv_id: str, user_id: str, cv_type: str, db: AsyncSession):
    """
    Unset a CV as primary (toggle off).
    """
    from app.models.cv_uploaded import CVUploaded

    if cv_type == "profile":
        result = await db.execute(
            select(cv_profile.CVProfile)
            .where(cv_profile.CVProfile.id == cv_id, cv_profile.CVProfile.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
    elif cv_type == "uploaded":
        result = await db.execute(
            select(CVUploaded)
            .where(CVUploaded.id == cv_id, CVUploaded.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Invalid cv_type")

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    cv.is_primary = False
    await db.commit()
    return {"status": "success", "message": "Đã bỏ đánh dấu CV chính"}