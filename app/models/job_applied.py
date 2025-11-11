from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class JobApplied(BaseModel):
    __tablename__ = 'job_applied'
    
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    cv_id = Column(String(36), ForeignKey('cv_profiles.id'), nullable=False)
    status = Column(String(20))  # 'sent' | 'reviewing' | 'accepted' | 'rejected'
    applied_at = Column(DateTime)
    
    # Relationships
    user = relationship('User', back_populates='job_applications')
    job = relationship('Job', back_populates='applications')
    cv_profile = relationship('CVProfile', back_populates='job_applications')
