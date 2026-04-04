"""
Job Document Model for MongoDB
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document
from pydantic import Field
from enum import Enum

class JobStatus(str, Enum):
    """Job status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    DRAFT = "draft"

class JobType(str, Enum):
    """Job type enumeration"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"

class ExperienceLevel(str, Enum):
    """Experience level enumeration"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"

class Job(Document):
    """Job posting document"""
    
    # Basic Information
    title: str
    description: str
    company_id: str  # Reference to Company document
    
    # Job Details
    job_type: JobType = JobType.FULL_TIME
    experience_level: ExperienceLevel = ExperienceLevel.ENTRY
    location: str
    remote_allowed: bool = False
    
    # Salary Information
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
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
    status: JobStatus = JobStatus.ACTIVE
    views_count: int = 0
    applications_count: int = 0
    featured: bool = False
    
    # SEO and Search
    tags: List[str] = Field(default_factory=list)
    category_ids: List[str] = Field(default_factory=list)  # Reference to PostgreSQL categories
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "jobs"
        indexes = [
            "company_id",
            "status",
            "job_type",
            "experience_level",
            "location",
            "created_at",
            "published_at",
            "application_deadline",
            "featured",
            [("title", "text"), ("description", "text")],  # Text search
            [("status", 1), ("featured", -1), ("created_at", -1)],  # Compound index for listing
            [("company_id", 1), ("status", 1)],  # Company jobs
            [("location", 1), ("status", 1)],  # Location-based search
        ]
    
    def __str__(self):
        return f"Job(title='{self.title}', company_id='{self.company_id}')"
    
    async def increment_views(self):
        """Increment view count"""
        await self.update({"$inc": {"views_count": 1}})
    
    async def increment_applications(self):
        """Increment application count"""
        await self.update({"$inc": {"applications_count": 1}})
    
    def is_expired(self) -> bool:
        """Check if job is expired"""
        if self.application_deadline:
            return datetime.utcnow() > self.application_deadline
        return False
    
    def is_active(self) -> bool:
        """Check if job is active and not expired"""
        return self.status == JobStatus.ACTIVE and not self.is_expired()