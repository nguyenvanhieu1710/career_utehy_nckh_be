from sqlalchemy import func, extract, case, desc, cast
from sqlalchemy.types import Numeric

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
import uuid
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from app.models import order
from app.schemas import get_schema
from passlib.context import CryptContext
from app.utils import auth
from sqlalchemy.exc import IntegrityError
import string
import secrets
import math
import calendar

async def get_revenue_by_month(year: int, db: AsyncSession):
    stmt = (
        select(
            extract("month", order.Orders.created_at).label("month"),
            func.sum(order.Orders.amount).label("total_revenue"),
            func.sum(
                case(
                    (order.Orders.status == 'PAID', order.Orders.amount),
                    else_=0
                )
            ).label("paid_revenue"),
        )
        .where(extract("year", order.Orders.created_at) == year)
        .group_by("month")
        .order_by("month")
    )

    result = await db.execute(stmt)
    rows = result.all()
    revenue_map = {
        int(month): {
            "total_revenue": float(total) if total else 0,
            "paid_revenue": float(paid) if paid else 0
        }
        for month, total, paid in rows
    }

    current_year = datetime.now().year
    current_month = datetime.now().month
    last_month = current_month if year == current_year else 12

    data = [
        {
            "month_num": m,
            "month": calendar.month_abbr[m],
            "total_revenue": revenue_map.get(m, {}).get("total_revenue", 0.0),
            "paid_revenue": revenue_map.get(m, {}).get("paid_revenue", 0.0),
        }
        for m in range(1, last_month + 1)
    ]

    return data
