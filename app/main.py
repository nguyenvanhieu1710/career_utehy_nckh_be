from fastapi import FastAPI
from app.api.v1 import email, payment, permission
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine, SessionLocal
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

@app.get("/")
def root():
    return {"msg": "backend is running"}
