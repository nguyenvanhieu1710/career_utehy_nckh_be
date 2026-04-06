from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from pydantic import BaseModel as BM

from sqlalchemy.dialects.postgresql import UUID
from typing import Optional

class CVProfile(BaseModel):
    __tablename__ = 'cv_profiles'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    title = Column(String(100), nullable=True)
    subtitle = Column(String(100), nullable=True)
    primary_color = Column(String(20), nullable=True)
    sections = Column(Text, nullable=False)
    design_data = Column(Text, nullable=False)
    
    # Relationships
    user = relationship('Users', back_populates='cv_profiles')

class CVSave(BM):
    name: Optional[str] = None
    id: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    primary_color: Optional[str] = None
    sections: Optional[str] = None
    template_id: Optional[str] = None