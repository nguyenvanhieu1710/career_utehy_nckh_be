from sqlalchemy import func, extract, case, desc, cast
from sqlalchemy.types import Numeric

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
import uuid
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from app.models.user import Users
from app.models.job_status import JobStatus
from app.models.crawl_history import CrawlHistory
from app.models.system_log import SystemLog

async def get_admin_dashboard_stats(days: int, db: AsyncSession):
    start_date = datetime.now() - timedelta(days=days)
    
    # Helper to execute and map results
    async def get_daily_counts(model, date_field, count_expr, filter_cond=None):
        stmt = (
            select(
                func.date(date_field).label("date"),
                count_expr.label("count")
            )
            .where(date_field >= start_date)
        )
        if filter_cond is not None:
            stmt = stmt.where(filter_cond)
        
        stmt = stmt.group_by(func.date(date_field)).order_by(func.date(date_field))
        
        result = await db.execute(stmt)
        return {str(row.date): row.count for row in result.all()}

    # Query metrics
    users_data = await get_daily_counts(Users, Users.created_at, func.count(Users.id))
    crawled_data = await get_daily_counts(
        CrawlHistory, 
        CrawlHistory.started_at, 
        func.sum(CrawlHistory.jobs_created + CrawlHistory.jobs_updated)
    )
    
    # Count unique visitors (by IP) from system logs
    visits_data = await get_daily_counts(
        SystemLog,
        SystemLog.created_at,
        func.count(func.distinct(SystemLog.ip_address)),
        filter_cond=(SystemLog.action_type == 'visit')
    )

    # Generate date range for the last N days
    chart_data = []
    for i in range(days + 1):
        date = (start_date + timedelta(days=i)).date()
        date_str = str(date)
        chart_data.append({
            "name": date.strftime("%d/%m"),
            "full_date": date_str,
            "registered_students": int(users_data.get(date_str, 0)),
            "jobs_crawled": int(crawled_data.get(date_str, 0)) if crawled_data.get(date_str) is not None else 0,
            "website_visits": int(visits_data.get(date_str, 0))
        })

    return chart_data
