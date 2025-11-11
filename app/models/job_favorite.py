from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class JobFavorite(BaseModel):
    __tablename__ = 'job_favorites'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)
    
    # Relationships
    user = relationship('Users', back_populates='favorite_jobs')
    job = relationship('Job', back_populates='favorites')
