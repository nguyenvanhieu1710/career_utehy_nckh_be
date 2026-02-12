"""
Alembic environment configuration for async SQLAlchemy
"""
import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL from environment variables
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_DATABASE')}"
)

# Import all SQLAlchemy models for autogenerate support
from app.models.base_model import BaseModel
from app.models.user import Users, UserRole, UserPerm
from app.models.category import Category
from app.models.company import Company
from app.models.job import Job
from app.models.job_favorite import JobFavorite
from app.models.job_status import JobStatus
from app.models.data_source import DataSource
from app.models.crawler_config import CrawlerConfig
from app.models.crawl_history import CrawlHistory
from app.models.cv_profile import CVProfile
from app.models.perm_groups import PermGroups, GroupPermission

# Use Base metadata for autogenerate
from app.core.database import Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()