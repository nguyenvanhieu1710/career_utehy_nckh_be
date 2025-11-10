from sqlalchemy import Column, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid

from app.core.database import Base


class GroupPermission(Base):
    __tablename__ = "group_permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("perm_groups.id", ondelete="CASCADE"))
    perm = Column(String, nullable=False)

    group = relationship("PermGroups", back_populates="permissions")


class PermGroups(Base):
    __tablename__ = "perm_groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    user_roles = relationship("UserRole", back_populates="group")

    permissions = relationship(
        "GroupPermission",
        back_populates="group",
        cascade="all, delete-orphan"
    )


class CreateGroup(BaseModel):
    name: str
    description: Optional[str] = None
    perms: Optional[List[str]] = [] 


