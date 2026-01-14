"""
Company Document Model for MongoDB
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document
from pydantic import Field, HttpUrl
from enum import Enum

class CompanySize(str, Enum):
    """Company size enumeration"""
    STARTUP = "startup"  # 1-10
    SMALL = "small"      # 11-50
    MEDIUM = "medium"    # 51-200
    LARGE = "large"      # 201-1000
    ENTERPRISE = "enterprise"  # 1000+

class CompanyStatus(str, Enum):
    """Company status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class Company(Document):
    """Company profile document"""
    
    # Basic Information
    name: str
    slug: str  # URL-friendly name
    description: str
    short_description: Optional[str] = None
    
    # Contact Information
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    
    # Location Information
    address: Optional[str] = None
    city: str
    country: str = "Vietnam"
    locations: List[str] = Field(default_factory=list)  # Multiple office locations
    
    # Company Details
    industry: str
    company_size: CompanySize = CompanySize.STARTUP
    founded_year: Optional[int] = None
    
    # Media
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Social Media
    linkedin_url: Optional[HttpUrl] = None
    facebook_url: Optional[HttpUrl] = None
    twitter_url: Optional[str] = None
    
    # Company Culture
    benefits: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    culture_description: Optional[str] = None
    
    # Statistics
    total_jobs: int = 0
    active_jobs: int = 0
    total_employees: Optional[int] = None
    followers_count: int = 0
    
    # Verification and Status
    verified: bool = False
    featured: bool = False
    status: CompanyStatus = CompanyStatus.PENDING
    
    # SEO and Search
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "companies"
        indexes = [
            "slug",
            "status",
            "verified",
            "featured",
            "industry",
            "city",
            "company_size",
            "created_at",
            [("name", "text"), ("description", "text"), ("industry", "text")],  # Text search
            [("status", 1), ("featured", -1), ("verified", -1), ("created_at", -1)],  # Listing
            [("city", 1), ("status", 1)],  # Location-based search
            [("industry", 1), ("status", 1)],  # Industry-based search
        ]
    
    def __str__(self):
        return f"Company(name='{self.name}', industry='{self.industry}')"
    
    async def increment_followers(self):
        """Increment followers count"""
        await self.update({"$inc": {"followers_count": 1}})
    
    async def decrement_followers(self):
        """Decrement followers count"""
        await self.update({"$inc": {"followers_count": -1}})
    
    async def update_job_counts(self):
        """Update job statistics"""
        from app.models.mongo.job import Job, JobStatus
        
        # Count total jobs
        total = await Job.find(Job.company_id == str(self.id)).count()
        
        # Count active jobs
        active = await Job.find(
            Job.company_id == str(self.id),
            Job.status == JobStatus.ACTIVE
        ).count()
        
        # Update counts
        await self.update({
            "$set": {
                "total_jobs": total,
                "active_jobs": active,
                "updated_at": datetime.utcnow()
            }
        })
    
    def is_active(self) -> bool:
        """Check if company is active"""
        return self.status == CompanyStatus.ACTIVE
    
    def get_display_size(self) -> str:
        """Get human-readable company size"""
        size_map = {
            CompanySize.STARTUP: "1-10 nhân viên",
            CompanySize.SMALL: "11-50 nhân viên", 
            CompanySize.MEDIUM: "51-200 nhân viên",
            CompanySize.LARGE: "201-1000 nhân viên",
            CompanySize.ENTERPRISE: "1000+ nhân viên"
        }
        return size_map.get(self.company_size, "Không xác định")