from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Users(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, index=False)
    fullname = Column(String, nullable=False)
    birthday = Column(Date, nullable=True)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
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


