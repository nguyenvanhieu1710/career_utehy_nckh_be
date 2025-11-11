from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class Job(BaseModel):
    __tablename__ = 'jobs'
    
    title = Column(String(200), nullable=False)
    slug = Column(String(255), unique=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    location = Column(String(150))
    other_locations = Column(JSON)
    work_arrangement = Column(String(50))
    job_type = Column(String(20))  # 'full-time', 'part-time', 'intern', 'freelance', 'contract'
    salary_display = Column(String(100))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    skills = Column(JSON)
    requirements = Column(Text)
    description = Column(Text)
    benefits = Column(Text)
    status = Column(String(20))  # 'pending', 'approved', 'rejected'
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    url_source = Column(String(255))
    posted_at = Column(DateTime)
    expired_at = Column(DateTime)
    
    # Relationships
    company = relationship('Company', back_populates='jobs')
    source = relationship('DataSource', back_populates='jobs')
    favorites = relationship('JobFavorite', back_populates='job')
    statuses = relationship('JobStatus', back_populates='job')
