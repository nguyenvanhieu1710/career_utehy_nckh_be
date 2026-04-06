from app.models import perm_groups, user
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import auth
from fastapi import HTTPException, status
from sqlalchemy.future import select
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc, delete
import math
from app.core.perms import require_permission
@require_permission(["role.create"])
async def create(user_perms: list[str], data: perm_groups.CreateGroup, db: AsyncSession):
    try:
        new_group = perm_groups.PermGroups(
            name=data.name,
            description=data.description
        )
        if data.perms:
            new_group.permissions = [
                perm_groups.GroupPermission(perm=perm)
                for perm in data.perms
            ]

        db.add(new_group)
        await db.commit()
        await db.refresh(new_group)

        return {"status": "success", "data": new_group}

    except Exception as ex:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(ex)}"
        )
@require_permission(["role.update"])
async def update(user_perms: list[str], group_id: str, data: perm_groups.CreateGroup, db: AsyncSession):
    try:
        result = await db.execute(select(perm_groups.PermGroups).where(perm_groups.PermGroups.id == group_id))
        group = result.scalars().first()

        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        group.name = data.name
        group.description = data.description
        await db.execute(
            delete(perm_groups.GroupPermission).where(
                perm_groups.GroupPermission.group_id == group_id
            )
        )
        if hasattr(data, "perms") and data.perms:
            for perm in data.perms:
                new_perm = perm_groups.GroupPermission(group_id=group_id, perm=perm)
                db.add(new_perm)
        await db.commit()
        await db.refresh(group)

        return {"status": "success", "data": group}

    except HTTPException:
        raise
    except Exception as ex:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(ex)}"
        )
@require_permission(["role.delete"])
async def delete_group(user_perms: list[str], id: str, db: AsyncSession):
    try:
        result = await db.execute(select(perm_groups.PermGroups).where(perm_groups.PermGroups.id == id))
        group = result.scalars().first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.execute(
            delete(perm_groups.GroupPermission).where(
                perm_groups.GroupPermission.group_id == id
            )
        )
        await db.delete(group)
        await db.commit()
        return {"status": "success", "message": "Group deleted successfully"}

    except HTTPException:
        raise
    except Exception as ex:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(ex)}"
        )
async def get(filters: get_schema.GetSchema, db: AsyncSession):
    stmt = (select(perm_groups.PermGroups).options(selectinload(perm_groups.PermGroups.permissions)))
    stmt = stmt.order_by(desc(perm_groups.PermGroups.created_at))

    if filters.id:
        stmt = stmt.filter(perm_groups.PermGroups.id == filters.id)
    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword.strip()}%"
        stmt = stmt.where(
            (perm_groups.PermGroups.name.ilike(keyword)) |
            (perm_groups.PermGroups.description.ilike(keyword))
        )
    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    result = await db.execute(stmt.offset(offset).limit(row))
    data = result.scalars().all()
    max_page = math.ceil(total / row) if row > 0 else 1

    return {
        "total": total,
        "page": page,
        "row": row,
        "max_page": max_page,
        "data": data
    }