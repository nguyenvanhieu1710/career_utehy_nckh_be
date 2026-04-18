import aiohttp
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job import Job
from app.models.company import Company
from app.models.import_log import MinioImportLog
from datetime import datetime
import uuid
import re
import os
import json
from minio import Minio
from io import BytesIO
import anyio

logger = logging.getLogger(__name__)

class ImportJobService:
    @staticmethod
    def get_minio_client():
        """Init MinIO client"""
        return Minio(
            os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=os.getenv("MINIO_SECURE").lower() == "true"
        )

    @staticmethod
    def generate_slug(text: str) -> str:
        """Generate a URL-friendly slug from text"""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')

    @staticmethod
    async def get_or_create_company(db: AsyncSession, company_name: str) -> uuid.UUID:
        """Find company by name, if not found then create new one"""
        if not company_name:
            company_name = "Unknown Company"
            
        result = await db.execute(select(Company).where(Company.name == company_name))
        company = result.scalar_one_or_none()
        
        if not company:
            base_slug = ImportJobService.generate_slug(company_name)
            unique_slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"
            
            company = Company(
                name=company_name,
                slug=unique_slug,
                action_status="active"
            )
            db.add(company)
            await db.flush()
            logger.info(f"Created new company: {company_name}")
        return company.id

    @staticmethod
    def map_job_type(raw_type: str) -> str:
        """Map raw employment type string to model ENUM-like values"""
        if not raw_type: return "full-time"
        raw_type = raw_type.lower()
        if "toàn thời gian" in raw_type or "full time" in raw_type: return "full-time"
        if "bán thời gian" in raw_type or "part time" in raw_type: return "part-time"
        if "thực tập" in raw_type or "intern" in raw_type: return "intern"
        if "freelance" in raw_type: return "freelance"
        if "hợp đồng" in raw_type or "contract" in raw_type: return "contract"
        return "full-time"

    @staticmethod
    async def process_job_items(db: AsyncSession, jobs_data: list, source_name: str):
        """Hàm lõi xử lý danh sách job và lưu vào DB"""
        count_success = 0
        count_error = 0
        
        for item in jobs_data:
            try:
                company_id = await ImportJobService.get_or_create_company(db, item.get("company_name"))
                title = item.get("job_title", "Untitled Job")
                
                tech_stack = item.get("tech_stack", "")
                skills = [s.strip() for s in tech_stack.split(",")] if tech_stack else []
                
                location = f"{item.get('location_district', '')}, {item.get('location_city', '')}".strip(", ")
                
                posted_at = datetime.utcnow()
                if item.get("post_date"):
                    try: posted_at = datetime.strptime(item.get("post_date"), "%Y-%m-%d")
                    except: pass
                    
                expired_at = None
                if item.get("application_deadline"):
                    try: expired_at = datetime.strptime(item.get("application_deadline"), "%Y-%m-%d")
                    except: pass

                unique_slug = f"{ImportJobService.generate_slug(title)}-{str(uuid.uuid4())[:8]}"
                
                # --- Check duplicate job ---
                job_check = await db.execute(
                    select(Job).where(Job.title == title, Job.company_id == company_id)
                )
                existing_job = job_check.scalar_one_or_none()
                
                if existing_job:
                    logger.info(f"Job already exists, skipping: {title}")
                    continue
                # ---------------------------
                
                new_job = Job(
                    title=title,
                    slug=unique_slug,
                    company_id=company_id,
                    location=location,
                    job_type=ImportJobService.map_job_type(item.get("employment_type")),
                    salary_display=(item.get("salary_text") or "")[:100],
                    salary_min=item.get("salary_min_usd"),
                    salary_max=item.get("salary_max_usd"),
                    skills=skills,
                    description=item.get("full_job_post_text") or item.get("job_summary"),
                    requirements=item.get("requirements"),
                    benefits=item.get("benefits"),
                    status="approved",
                    url_source=source_name[:255], # Truncate to avoid field length error
                    posted_at=posted_at,
                    expired_at=expired_at,
                    action_status="active"
                )
                
                db.add(new_job)
                count_success += 1
            except Exception as e:
                logger.error(f"Error importing item: {str(e)}")
                count_error += 1
                await db.rollback()
        
        await db.commit()
        return count_success, count_error

    @staticmethod
    async def import_from_url(db: AsyncSession, url: str):
        """Fetch JSON from URL and import (Lạc hậu hơn dùng MinIO SDK)"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=30.0) as response:
                    if response.status != 200:
                        return {"status": "error", "message": f"HTTP Error {response.status}"}
                    jobs_data = await response.json(content_type=None)
                    
                    if not isinstance(jobs_data, list): jobs_data = [jobs_data]
                    success, error = await ImportJobService.process_job_items(db, jobs_data, url)
                    return {"status": "success", "imported": success, "failed": error}
            except Exception as e:
                await db.rollback()
                return {"status": "error", "message": str(e)}

    @staticmethod
    async def import_from_minio(db: AsyncSession, bucket: str, object_name: str):
        """Get file directly from MinIO via SDK and import into DB"""
        client = ImportJobService.get_minio_client()
        
        try:
            # Hàm sync được bọc để chạy trong threadpool giúp tránh block FastAPI
            def fetch_data():
                response = client.get_object(bucket, object_name)
                try:
                    return json.loads(response.read().decode("utf-8"))
                finally:
                    response.close()
                    response.release_conn()

            jobs_data = await anyio.to_thread.run_sync(fetch_data)
            
            if not isinstance(jobs_data, list):
                jobs_data = [jobs_data]
                
            success, error = await ImportJobService.process_job_items(db, jobs_data, f"minio://{bucket}/{object_name}")
            
            return {
                "status": "success",
                "imported": success,
                "failed": error,
                "source": f"{bucket}/{object_name}"
            }
        except Exception as e:
            logger.error(f"MinIO Import Error: {str(e)}")
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def smart_scan_and_import(db: AsyncSession, bucket: str = "crawl-results"):
        """Scan MinIO bucket and automatically import new Stage 3 files"""
        client = ImportJobService.get_minio_client()
        
        try:
            # 1. List all objects in bucket (run in thread)
            def list_objects():
                return list(client.list_objects(bucket, recursive=True))

            objects = await anyio.to_thread.run_sync(list_objects)
            
            # 2. Filter: Only get Stage 3 files and .json format
            candidate_files = [
                obj for obj in objects 
                if "stage3" in obj.object_name.lower() and 
                obj.object_name.endswith(".json") and 
                not obj.is_dir
            ]
            
            logger.info(f"Scanning bucket {bucket}: Found {len(candidate_files)} potential Stage 3 files.")
            
            summary = {"total_found": len(candidate_files), "new_processed": 0, "skipped": 0, "failed": 0}
            
            for obj in candidate_files:
                # 3. Check if this file has been successfully processed (based on name and etag)
                stmt = select(MinioImportLog).where(
                    MinioImportLog.bucket_name == bucket,
                    MinioImportLog.object_name == obj.object_name,
                    MinioImportLog.etag == obj.etag,
                    MinioImportLog.status == "success"
                )
                result = await db.execute(stmt)
                if result.scalar_one_or_none():
                    summary["skipped"] += 1
                    continue
                
                # 4. Import
                logger.info(f"Processing new file: {obj.object_name}")
                import_res = await ImportJobService.import_from_minio(db, bucket, obj.object_name)
                
                # 5. Log Import
                new_log = MinioImportLog(
                    bucket_name=bucket,
                    object_name=obj.object_name,
                    etag=obj.etag,
                    status=import_res["status"],
                    error_message=import_res.get("message") if import_res["status"] == "error" else None,
                    processed_at=datetime.utcnow()
                )
                db.add(new_log)
                # Commit after each file to ensure each file is recorded once completed
                await db.commit() 
                
                if import_res["status"] == "success":
                    summary["new_processed"] += 1
                else:
                    summary["failed"] += 1
                    
            return summary
            
        except Exception as e:
            logger.error(f"Smart Scan Task Error: {str(e)}")
            return {"status": "error", "message": str(e)}
