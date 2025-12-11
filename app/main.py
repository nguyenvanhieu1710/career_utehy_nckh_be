from fastapi import FastAPI
from app.api.v1 import email, payment, permission, auth, cv, category, job, company 
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine, SessionLocal
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


app = FastAPI()

async def get_db():
    async with SessionLocal() as session:
        yield session

# Khởi tạo DB (chạy 1 lần lúc start)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

app.include_router(email.router, prefix="/api/v1/email", tags=["Email"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["Payment"])
app.include_router(permission.router, prefix="/api/v1/permission", tags=["Permission"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(cv.router, prefix="/api/v1/cv", tags=["CV"])
app.include_router(category.router, prefix="/api/v1/category", tags=["Category"])
app.include_router(job.router, prefix="/api/v1/job", tags=["Job"])
app.include_router(company.router, prefix="/api/v1/company", tags=["Company"])

@app.get("/")
def root():
    return {"msg": "backend is running"}
