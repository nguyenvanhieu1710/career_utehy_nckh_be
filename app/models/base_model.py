from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func
from uuid import uuid4
from pydantic import BaseModel
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID

def generate_uuid():
    return uuid4()  # Return UUID object, not string

class BaseModel(Base):
    """Base model with common fields and methods"""
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    action_status = Column(String(20), default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
