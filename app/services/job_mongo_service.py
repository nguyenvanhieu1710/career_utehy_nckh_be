"""
Job Service for MongoDB operations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from beanie import PydanticObjectId
from beanie.operators import RegEx, In, And, Or
from app.models.mongo.job import Job, JobStatus, JobType, ExperienceLevel
from app.schemas.job_mongo import JobCreateSchema, JobUpdateSchema, JobSearchSchema
import logging

logger = logging.getLogger(__name__)

class JobMongoService:
    """Service for handling job operations in MongoDB"""
    
    @staticmethod
    async def create_job(job_data: JobCreateSchema) -> Job:
        """Create a new job"""
        try:
            job = Job(**job_data.dict())
            job.published_at = datetime.utcnow() if job.status == JobStatus.ACTIVE else None
            await job.insert()
            logger.info(f"Created job: {job.id}")
            return job
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    @staticmethod
    async def get_job_by_id(job_id: str) -> Optional[Job]:
        """Get job by ID"""
        try:
            if not PydanticObjectId.is_valid(job_id):
                return None
            return await Job.get(PydanticObjectId(job_id))
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    @staticmethod
    async def update_job(job_id: str, job_data: JobUpdateSchema) -> Optional[Job]:
        """Update job"""
        try:
            if not PydanticObjectId.is_valid(job_id):
                return None
            
            job = await Job.get(PydanticObjectId(job_id))
            if not job:
                return None
            
            # Update fields
            update_data = job_data.dict(exclude_unset=True)
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                
                # Handle status change to active
                if "status" in update_data and update_data["status"] == JobStatus.ACTIVE:
                    if not job.published_at:
                        update_data["published_at"] = datetime.utcnow()
                
                await job.update({"$set": update_data})
                await job.reload()
            
            logger.info(f"Updated job: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            raise
    
    @staticmethod
    async def delete_job(job_id: str) -> bool:
        """Delete job"""
        try:
            if not PydanticObjectId.is_valid(job_id):
                return False
            
            job = await Job.get(PydanticObjectId(job_id))
            if not job:
                return False
            
            await job.delete()
            logger.info(f"Deleted job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            raise
    
    @staticmethod
    async def search_jobs(search_params: JobSearchSchema) -> Tuple[List[Job], int]:
        """Search jobs with filters and pagination"""
        try:
            # Build query conditions
            conditions = []
            
            # Status filter
            if search_params.status:
                conditions.append(Job.status == search_params.status)
            
            # Text search
            if search_params.query:
                conditions.append(
                    Or(
                        RegEx(Job.title, search_params.query, "i"),
                        RegEx(Job.description, search_params.query, "i")
                    )
                )
            
            # Location filter
            if search_params.location:
                conditions.append(RegEx(Job.location, search_params.location, "i"))
            
            # Job type filter
            if search_params.job_type:
                conditions.append(Job.job_type == search_params.job_type)
            
            # Experience level filter
            if search_params.experience_level:
                conditions.append(Job.experience_level == search_params.experience_level)
            
            # Company filter
            if search_params.company_id:
                conditions.append(Job.company_id == search_params.company_id)
            
            # Category filter
            if search_params.category_ids:
                conditions.append(In(Job.category_ids, search_params.category_ids))
            
            # Salary filters
            if search_params.salary_min:
                conditions.append(Job.salary_min >= search_params.salary_min)
            if search_params.salary_max:
                conditions.append(Job.salary_max <= search_params.salary_max)
            
            # Remote filter
            if search_params.remote_allowed is not None:
                conditions.append(Job.remote_allowed == search_params.remote_allowed)
            
            # Featured filter
            if search_params.featured is not None:
                conditions.append(Job.featured == search_params.featured)
            
            # Build final query
            if conditions:
                query = Job.find(And(*conditions))
            else:
                query = Job.find()
            
            # Get total count
            total = await query.count()
            
            # Apply sorting
            sort_field = getattr(Job, search_params.sort_by, Job.created_at)
            if search_params.sort_order == "desc":
                query = query.sort(-sort_field)
            else:
                query = query.sort(sort_field)
            
            # Apply pagination
            skip = (search_params.page - 1) * search_params.size
            jobs = await query.skip(skip).limit(search_params.size).to_list()
            
            return jobs, total
        except Exception as e:
            logger.error(f"Failed to search jobs: {e}")
            raise
    
    @staticmethod
    async def get_jobs_by_company(company_id: str, status: Optional[JobStatus] = None, limit: int = 10) -> List[Job]:
        """Get jobs by company"""
        try:
            conditions = [Job.company_id == company_id]
            if status:
                conditions.append(Job.status == status)
            
            return await Job.find(And(*conditions)).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to get jobs for company {company_id}: {e}")
            raise
    
    @staticmethod
    async def get_featured_jobs(limit: int = 10) -> List[Job]:
        """Get featured jobs"""
        try:
            return await Job.find(
                Job.featured == True,
                Job.status == JobStatus.ACTIVE
            ).sort(-Job.created_at).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to get featured jobs: {e}")
            raise
    
    @staticmethod
    async def get_recent_jobs(limit: int = 10) -> List[Job]:
        """Get recent jobs"""
        try:
            return await Job.find(
                Job.status == JobStatus.ACTIVE
            ).sort(-Job.created_at).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            raise
    
    @staticmethod
    async def increment_job_views(job_id: str) -> bool:
        """Increment job view count"""
        try:
            if not PydanticObjectId.is_valid(job_id):
                return False
            
            job = await Job.get(PydanticObjectId(job_id))
            if job:
                await job.increment_views()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to increment views for job {job_id}: {e}")
            return False
    
    @staticmethod
    async def increment_job_applications(job_id: str) -> bool:
        """Increment job application count"""
        try:
            if not PydanticObjectId.is_valid(job_id):
                return False
            
            job = await Job.get(PydanticObjectId(job_id))
            if job:
                await job.increment_applications()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to increment applications for job {job_id}: {e}")
            return False
    
    @staticmethod
    async def get_job_stats() -> Dict[str, Any]:
        """Get job statistics"""
        try:
            # Count by status
            total_jobs = await Job.find().count()
            active_jobs = await Job.find(Job.status == JobStatus.ACTIVE).count()
            inactive_jobs = await Job.find(Job.status == JobStatus.INACTIVE).count()
            expired_jobs = await Job.find(Job.status == JobStatus.EXPIRED).count()
            draft_jobs = await Job.find(Job.status == JobStatus.DRAFT).count()
            featured_jobs = await Job.find(Job.featured == True).count()
            
            # Count by job type
            jobs_by_type = {}
            for job_type in JobType:
                count = await Job.find(Job.job_type == job_type).count()
                jobs_by_type[job_type.value] = count
            
            # Count by experience level
            jobs_by_experience = {}
            for exp_level in ExperienceLevel:
                count = await Job.find(Job.experience_level == exp_level).count()
                jobs_by_experience[exp_level.value] = count
            
            # Top locations (simplified - in production use aggregation)
            jobs_by_location = {}
            jobs = await Job.find().limit(1000).to_list()
            for job in jobs:
                location = job.location
                jobs_by_location[location] = jobs_by_location.get(location, 0) + 1
            
            # Sort and limit top 10 locations
            jobs_by_location = dict(sorted(jobs_by_location.items(), key=lambda x: x[1], reverse=True)[:10])
            
            return {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "inactive_jobs": inactive_jobs,
                "expired_jobs": expired_jobs,
                "draft_jobs": draft_jobs,
                "featured_jobs": featured_jobs,
                "jobs_by_type": jobs_by_type,
                "jobs_by_experience": jobs_by_experience,
                "jobs_by_location": jobs_by_location
            }
        except Exception as e:
            logger.error(f"Failed to get job stats: {e}")
            raise

# Global service instance
job_mongo_service = JobMongoService()