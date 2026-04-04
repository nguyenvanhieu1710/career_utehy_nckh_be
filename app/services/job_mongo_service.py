"""
Job Service for MongoDB operations
Query jobs from companies collection (nested structure)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from app.core.mongodb import get_database
from app.schemas.job_mongo import JobCreateSchema, JobUpdateSchema, JobSearchSchema
import logging

logger = logging.getLogger(__name__)


def convert_objectid_to_str(data: Any) -> Any:
    """Recursively convert ObjectId to string in nested structures"""
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    return data

class JobMongoService:
    """Service for handling job operations in MongoDB (companies collection)"""
    
    @staticmethod
    async def get_all_jobs_from_companies() -> List[Dict[str, Any]]:
        """Get all jobs from companies collection (nested structure)"""
        try:
            db = get_database()
            companies_collection = db["companies"]
            
            # Get all companies
            companies = await companies_collection.find({}).to_list(length=None)
            
            all_jobs = []
            for company in companies:
                company_name = company.get("name", "Unknown Company")
                company_id = str(company.get("_id", ""))
                company_jobs = company.get("jobs", [])
                
                for job in company_jobs:
                    # Convert ObjectId and add company info
                    job_dict = convert_objectid_to_str(job)
                    job_dict["company_name"] = company_name
                    job_dict["company_id"] = company_id
                    all_jobs.append(job_dict)
            
            return all_jobs
        except Exception as e:
            logger.error(f"Failed to get all jobs: {e}")
            raise
    
    @staticmethod
    async def search_jobs(search_params: JobSearchSchema) -> Tuple[List[Dict[str, Any]], int]:
        """Search jobs with filters and pagination"""
        try:
            # Get all jobs first
            all_jobs = await JobMongoService.get_all_jobs_from_companies()
            
            # Apply filters
            filtered_jobs = []
            
            for job in all_jobs:
                # Text search in title/description
                if search_params.query:
                    query_lower = search_params.query.lower()
                    title = str(job.get("title", "")).lower()
                    description = str(job.get("description", "")).lower()
                    if query_lower not in title and query_lower not in description:
                        continue
                
                # Location filter
                if search_params.location:
                    location_lower = search_params.location.lower()
                    job_location = str(job.get("location", "")).lower()
                    if location_lower not in job_location:
                        continue
                
                # Job type filter
                if search_params.job_type:
                    if job.get("jobType") != search_params.job_type:
                        continue
                
                # Experience level filter
                if search_params.experience_level:
                    if job.get("experienceLevel") != search_params.experience_level:
                        continue
                
                # Company filter
                if search_params.company_id:
                    if job.get("company_id") != search_params.company_id:
                        continue
                
                # Remote filter
                if search_params.remote_allowed is not None:
                    if job.get("remoteAllowed") != search_params.remote_allowed:
                        continue
                
                # Featured filter
                if search_params.featured is not None:
                    if job.get("featured") != search_params.featured:
                        continue
                
                # Salary filters
                if search_params.salary_min:
                    job_salary_min = job.get("salaryMin", 0)
                    if job_salary_min < search_params.salary_min:
                        continue
                
                if search_params.salary_max:
                    job_salary_max = job.get("salaryMax", float('inf'))
                    if job_salary_max > search_params.salary_max:
                        continue
                
                filtered_jobs.append(job)
            
            total = len(filtered_jobs)
            
            # Apply sorting
            sort_field_map = {
                "created_at": "createdAt",
                "title": "title",
                "salary_min": "salaryMin",
                "salary_max": "salaryMax"
            }
            sort_field = sort_field_map.get(search_params.sort_by, "createdAt")
            reverse = search_params.sort_order == "desc"
            
            try:
                filtered_jobs.sort(
                    key=lambda x: x.get(sort_field, ""),
                    reverse=reverse
                )
            except Exception as e:
                logger.warning(f"Sorting failed: {e}, using default order")
            
            # Apply pagination
            start = (search_params.page - 1) * search_params.size
            end = start + search_params.size
            paginated_jobs = filtered_jobs[start:end]
            
            return paginated_jobs, total
        except Exception as e:
            logger.error(f"Failed to search jobs: {e}")
            raise
    
    @staticmethod
    async def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID from companies collection"""
        try:
            all_jobs = await JobMongoService.get_all_jobs_from_companies()
            
            for job in all_jobs:
                if job.get("id") == job_id:
                    return job
            
            return None
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    @staticmethod
    async def get_jobs_by_company(company_id: str, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get jobs by company"""
        try:
            db = get_database()
            companies_collection = db["companies"]
            
            # Find company by ID
            if ObjectId.is_valid(company_id):
                company = await companies_collection.find_one({"_id": ObjectId(company_id)})
            else:
                company = await companies_collection.find_one({"id": company_id})
            
            if not company:
                return []
            
            company_name = company.get("name", "Unknown Company")
            company_jobs = company.get("jobs", [])
            
            # Add company info and filter by status if provided
            jobs = []
            for job in company_jobs:
                if status and job.get("status") != status:
                    continue
                
                # Convert ObjectId and add company info
                job_dict = convert_objectid_to_str(job)
                job_dict["company_name"] = company_name
                job_dict["company_id"] = str(company.get("_id", ""))
                jobs.append(job_dict)
                
                if len(jobs) >= limit:
                    break
            
            return jobs
        except Exception as e:
            logger.error(f"Failed to get jobs for company {company_id}: {e}")
            raise
    
    @staticmethod
    async def get_featured_jobs(limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured jobs"""
        try:
            all_jobs = await JobMongoService.get_all_jobs_from_companies()
            
            # Filter featured jobs
            featured_jobs = [job for job in all_jobs if job.get("featured") == True]
            
            # Sort by created date (newest first)
            try:
                featured_jobs.sort(
                    key=lambda x: x.get("createdAt", ""),
                    reverse=True
                )
            except:
                pass
            
            return featured_jobs[:limit]
        except Exception as e:
            logger.error(f"Failed to get featured jobs: {e}")
            raise
    
    @staticmethod
    async def get_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs"""
        try:
            all_jobs = await JobMongoService.get_all_jobs_from_companies()
            
            # Sort by created date (newest first)
            try:
                all_jobs.sort(
                    key=lambda x: x.get("createdAt", ""),
                    reverse=True
                )
            except:
                pass
            
            return all_jobs[:limit]
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            raise
    
    @staticmethod
    async def get_job_stats() -> Dict[str, Any]:
        """Get job statistics"""
        try:
            all_jobs = await JobMongoService.get_all_jobs_from_companies()
            
            total_jobs = len(all_jobs)
            
            # Count by status
            status_counts = {}
            for job in all_jobs:
                status = job.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count featured
            featured_jobs = sum(1 for job in all_jobs if job.get("featured") == True)
            
            # Count by job type
            jobs_by_type = {}
            for job in all_jobs:
                job_type = job.get("jobType", "unknown")
                jobs_by_type[job_type] = jobs_by_type.get(job_type, 0) + 1
            
            # Count by experience level
            jobs_by_experience = {}
            for job in all_jobs:
                exp_level = job.get("experienceLevel", "unknown")
                jobs_by_experience[exp_level] = jobs_by_experience.get(exp_level, 0) + 1
            
            # Count by location (top 10)
            jobs_by_location = {}
            for job in all_jobs:
                location = job.get("location", "unknown")
                jobs_by_location[location] = jobs_by_location.get(location, 0) + 1
            
            # Sort and limit top 10 locations
            jobs_by_location = dict(sorted(jobs_by_location.items(), key=lambda x: x[1], reverse=True)[:10])
            
            return {
                "total_jobs": total_jobs,
                "active_jobs": status_counts.get("active", 0),
                "inactive_jobs": status_counts.get("inactive", 0),
                "expired_jobs": status_counts.get("expired", 0),
                "draft_jobs": status_counts.get("draft", 0),
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