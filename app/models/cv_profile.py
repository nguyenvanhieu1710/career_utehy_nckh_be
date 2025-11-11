from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class CVProfile(BaseModel):
    __tablename__ = 'cv_profiles'
    
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    title = Column(String(100), nullable=False)
    summary = Column(Text)    
    projects = Column(JSON)
    certifications = Column(JSON)
    languages = Column(JSON)
    file_url = Column(String(255))
    
    # Relationships
    user = relationship('User', back_populates='cv_profiles')
    job_applications = relationship('JobApplied', back_populates='cv_profile')
