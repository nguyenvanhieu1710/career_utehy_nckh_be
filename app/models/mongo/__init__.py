"""
MongoDB Document Models

This package contains all MongoDB document models using Beanie ODM.
These models are separate from SQLAlchemy models and handle unstructured data.
"""

# Import main document models
from .job import Job, JobStatus, JobType, ExperienceLevel
from .company import Company, CompanySize, CompanyStatus

__all__ = [
    # Main models
    "Job",
    "JobStatus", 
    "JobType",
    "ExperienceLevel",
    "Company",
    "CompanySize",
    "CompanyStatus",
]