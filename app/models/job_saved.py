from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class JobSaved(BaseModel):
    __tablename__ = 'job_saved'
    
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='saved_jobs')
    job = relationship('Job', back_populates='saved_by')
