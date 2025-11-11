from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.sql import func
from .base_model import BaseModel
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

class JobStatus(BaseModel):
    __tablename__ = 'job_status'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)
    status = Column(String(20), nullable=False)  # 'suggested', 'viewed', 'saved', 'ignored'
    
    # Relationships
    user = relationship('Users', back_populates='job_statuses')
    job = relationship('Job', back_populates='statuses')
