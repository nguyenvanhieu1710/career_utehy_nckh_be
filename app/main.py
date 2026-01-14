from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1 import email, payment, permission, auth, cv, category, job, company, upload, common, public, job_mongo, chat
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.static_files import StaticFileSecurityMiddleware
import os
# from services.vector_service import build_faiss_index
from app.core.database import Base, engine, SessionLocal
from app.core.mongodb import connect_to_mongo, close_mongo_connection, mongodb_health_check
from app.models.base_model import BaseModel
from app.models.category import Category
from app.models.company import Company
from app.models.job import Job
from app.models.crawler_config import CrawlerConfig
from app.models.cv_profile import CVProfile
from app.models.data_source import DataSource
from app.models.job_favorite import JobFavorite
from app.models.user import UserPerm, UserRole, Users
from app.models.perm_groups import PermGroups, GroupPermission
from app.models.job_status import JobStatus

from pydantic import BaseModel, EmailStr
import logging
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI(
    # root_path="/api",
    title="Career UTEHY API",
    description="Student Job Recommendation System API",
    version="1.0.0"
)

async def get_db():
    async with SessionLocal() as session:
        yield session

# Khởi tạo DB và uploads directory (chạy 1 lần lúc start)
@app.on_event("startup")
async def startup():
    # Initialize PostgreSQL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize MongoDB
    try:
        await connect_to_mongo()
        # logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.error(f"❌ MongoDB failed: {e}")
        # Don't stop the app if MongoDB fails, just log the error
    
    # LOAD FAISS KHI START APP
    # build_faiss_index()

    # Log API documentation URL
    logger.info("📚 Swagger UI: http://localhost:8000/docs")
    
    # Ensure uploads directory exists
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir, exist_ok=True)
    
    # Create subdirectories for different file types
    subdirs = ["users", "categories", "data-sources", "jobs", "companies", "cv"]
    for subdir in subdirs:
        subdir_path = os.path.join(uploads_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path, exist_ok=True)
    
    # Seed initial data (admin user)
    try:
        from app.services.seed_service import seed_initial_data
        await seed_initial_data()
    except Exception as e:
        print(f"⚠️ Warning: Failed to seed initial data: {str(e)}")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on app shutdown"""
    await close_mongo_connection()
    logger.info("Application shutdown complete")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4000",
    "http://localhost:4000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add static file security middleware
app.add_middleware(StaticFileSecurityMiddleware, uploads_path="uploads")

app.include_router(email.router, prefix="/api/v1/email", tags=["Email"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["Payment"])
app.include_router(permission.router, prefix="/api/v1/permission", tags=["Permission"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(cv.router, prefix="/api/v1/cv", tags=["CV"])
app.include_router(category.router, prefix="/api/v1/category", tags=["Category"])
app.include_router(job.router, prefix="/api/v1/job", tags=["Job"])
app.include_router(job_mongo.router, prefix="/api/v1/job-mongo", tags=["Job MongoDB"])
app.include_router(company.router, prefix="/api/v1/company", tags=["Company"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(common.router, prefix="/api/v1/common", tags=["Common"])
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

# Static file serving for uploads
uploads_dir = "uploads"
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Custom static file handler with security and caching
@app.get("/static/uploads/{file_path:path}")
async def serve_upload_file(file_path: str):
    """
    Serve uploaded files with proper security and caching headers
    """
    full_path = os.path.join(uploads_dir, file_path)
    
    # Security check: ensure path is within uploads directory
    uploads_abs = os.path.abspath(uploads_dir)
    requested_abs = os.path.abspath(full_path)
    
    if not requested_abs.startswith(uploads_abs):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if file exists and is actually a file
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Get file extension for proper MIME type
    from pathlib import Path
    file_ext = Path(full_path).suffix.lower()
    media_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff'
    }
    
    media_type = media_type_map.get(file_ext, 'application/octet-stream')
    
    # Return file with proper headers
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=os.path.basename(full_path),
        headers={
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
            "ETag": f'"{os.path.getmtime(full_path)}"',   # ETag for caching
            "X-Content-Type-Options": "nosniff",          # Security header
            "X-Frame-Options": "DENY",                    # Prevent embedding
        }
    )

@app.get("/")
def root():
    return {
        "msg": "backend is running",
        "version": "1.0.0",
        "upload_system": "enabled",
        "static_files": "/uploads",
        "databases": {
            "postgresql": "connected",
            "mongodb": "connected" if mongodb_health_check else "disconnected"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for both databases"""
    postgres_healthy = True  # Assume healthy if app is running
    mongo_healthy = await mongodb_health_check()
    
    return {
        "status": "healthy" if postgres_healthy and mongo_healthy else "degraded",
        "databases": {
            "postgresql": "healthy" if postgres_healthy else "unhealthy",
            "mongodb": "healthy" if mongo_healthy else "unhealthy"
        },
        "timestamp": os.environ.get("TIMESTAMP", "unknown")
    }
