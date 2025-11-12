from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class CVProfile(BaseModel):
    __tablename__ = 'cv_profiles'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(100), nullable=True)
    subtitle = Column(String(100), nullable=True)
    about = Column(String, nullable=True)
    personal_infomations = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)
    tech_skills = Column(JSON, nullable=True)
    experiences = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    
    # Relationships
    user = relationship('Users', back_populates='cv_profiles')
