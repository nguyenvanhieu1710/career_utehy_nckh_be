from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Users(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, index=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    avatar_url = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    unversity = Column(String, nullable=False)
    major = Column(String, nullable=False)
    graduation_year = Column(String, nullable=False)
    experience = Column(String, nullable=False)
    bio = Column(String, nullable=False)
    status = Column(String, nullable=False)
    action_status = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Users", back_populates="user_info")

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("perm_groups.id"))
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Users", back_populates="roles")
    group = relationship("PermGroups", back_populates="user_roles")


class UserPerm(Base):
    __tablename__ = "user_perms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    perm = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Users", back_populates="permissions")

class UserSignin(BaseModel):
    email: str
    username: str
    password: str
    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class AddPerm(BaseModel):
    user_id: str
    perm: str

class AddRole(BaseModel):
    user_id: str
    group_id: str


