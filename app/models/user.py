from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Users(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    username = Column(String, index=False)
    fullname = Column(String, nullable=False)
    birthday = Column(Date, nullable=True)    
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    unversity = Column(String, nullable=True)
    major = Column(String, nullable=True)
    graduation_year = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    bio = Column(String, nullable=True)

    action_status = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    roles = relationship("UserRole", back_populates="user")
    permissions = relationship("UserPerm", back_populates="user")
    job_statuses = relationship("JobStatus", back_populates="user")
    cv_profiles = relationship("CVProfile", back_populates="user")
    favorite_jobs = relationship("JobFavorite", back_populates="user")

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
    fullname: Optional[str] = None
    class Config:
        from_attributes = True

class UserCreateByAdmin(BaseModel):
    email: str
    username: str
    password: str
    fullname: str
    role_ids: Optional[List[str]] = []
    permissions: Optional[List[str]] = []
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    fullname: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    action_status: Optional[str] = None
    role_ids: Optional[List[str]] = None
    permissions: Optional[List[str]] = None

class AddPerm(BaseModel):
    user_id: str
    perm: str

class AddRole(BaseModel):
    user_id: str
    group_id: str

class UserWithRoles(BaseModel):
    id: str
    email: str
    fullname: str
    username: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    action_status: Optional[str] = None
    roles: List[dict] = []  # [{"id": "...", "name": "Admin", "description": "..."}]
    permissions: List[str] = []  # ["user.create", "user.update"]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AvailableRole(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class UpdateUserRoles(BaseModel):
    role_ids: List[str] = []
    permissions: List[str] = []


