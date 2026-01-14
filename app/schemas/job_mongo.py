"""
Job Schemas for MongoDB API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.mongo.job import JobStatus, JobType, ExperienceLevel

class JobCreateSchema(BaseModel):
    """Schema for creating a new job"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    company_id: str = Field(..., description="MongoDB ObjectId of the company")
    
    # Job Details
    job_type: JobType = JobType.FULL_TIME
    experience_level: ExperienceLevel = ExperienceLevel.ENTRY
    location: str = Field(..., min_length=1)
    remote_allowed: bool = False
    
    # Salary Information
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = "VND"
    salary_negotiable: bool = True
    
    # Requirements
    requirements: List[str] = Field(default_factory=list)
    skills_required: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    
    # Application Information
    application_deadline: Optional[datetime] = None
    application_email: Optional[str] = None
    application_url: Optional[str] = None
    
    # Metadata
    featured: bool = False
    tags: List[str] = Field(default_factory=list)
    category_ids: List[str] = Field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JobUpdateSchema(BaseModel):
    """Schema for updating a job"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    
    # Job Details
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    location: Optional[str] = Field(None, min_length=1)
    remote_allowed: Optional[bool] = None
    
    # Salary Information
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = None
    salary_negotiable: Optional[bool] = None
    
    # Requirements
    requirements: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    
    # Application Information
    application_deadline: Optional[datetime] = None
    application_email: Optional[str] = None
    application_url: Optional[str] = None
    
    # Metadata
    status: Optional[JobStatus] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None

class JobResponseSchema(BaseModel):
    """Schema for job response"""
    id: str = Field(..., description="MongoDB ObjectId as string")
    title: str
    description: str
    company_id: str
    
    # Job Details
    job_type: JobType
    experience_level: ExperienceLevel
    location: str
    remote_allowed: bool
    
    # Salary Information
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: str
    salary_negotiable: bool
    
    # Requirements
    requirements: List[str]
    skills_required: List[str]
    benefits: List[str]
    
    # Application Information
    application_deadline: Optional[datetime]
    application_email: Optional[str]
    application_url: Optional[str]
    
    # Metadata
    status: JobStatus
    views_count: int
    applications_count: int
    featured: bool
    tags: List[str]
    category_ids: List[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    
    # Additional metadata
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

class JobListResponseSchema(BaseModel):
    """Schema for job list response"""
    jobs: List[JobResponseSchema]
    total: int
    page: int
    size: int
    total_pages: int

class JobSearchSchema(BaseModel):
    """Schema for job search parameters"""
    query: Optional[str] = Field(None, description="Search query for title/description")
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    company_id: Optional[str] = None
    category_ids: Optional[List[str]] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    remote_allowed: Optional[bool] = None
    featured: Optional[bool] = None
    status: Optional[JobStatus] = JobStatus.ACTIVE
    
    # Pagination
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    
    # Sorting
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")

class JobStatsSchema(BaseModel):
    """Schema for job statistics"""
    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    expired_jobs: int
    draft_jobs: int
    featured_jobs: int
    jobs_by_type: Dict[str, int]
    jobs_by_experience: Dict[str, int]
    jobs_by_location: Dict[str, int]