from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base_model import BaseModel

class JobStatus(BaseModel):
    __tablename__ = 'job_status'
    
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    status = Column(String(20), nullable=False)  # 'suggested', 'viewed', 'saved', 'ignored'
    
    # Relationships
    user = relationship('User', back_populates='job_statuses')
    job = relationship('Job', back_populates='statuses')
