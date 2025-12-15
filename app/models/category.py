from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel as PydanticBaseModel
from typing import Optional

class Category(BaseModel):
    __tablename__ = 'categories'
    
    avatar_url = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('categories.id'), nullable=True)
    description = Column(Text)
    
    # Self-referential relationship for parent-child categories
    parent = relationship('Category', remote_side='Category.id', backref='subcategories')


# Pydantic models for API
class CategoryCreate(PydanticBaseModel):
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        orm_mode = True


class CategoryUpdate(PydanticBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        orm_mode = True


class CategoryResponse(PydanticBaseModel):
    id: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    action_status: str
    created_at: str
    updated_at: str
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None
    
    class Config:
        orm_mode = True
