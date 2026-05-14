from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class GetSchema(BaseModel):
    id: Optional[str] = None
    searchKeyword: Optional[str] = None
    page: Optional[int] = None
    row: Optional[int] = None
    role_id: Optional[str] = None
    status: Optional[str] = None
    sortBy: Optional[str] = None
    sortOrder: Optional[str] = "desc"  # "asc" or "desc"

class GetBlogSchema(BaseModel):
    user_id: Optional[str] = None
    tag: Optional[str] = None
    id: Optional[str] = None
    searchKeyword: Optional[str] = None
    page: Optional[int] = None
    row: Optional[int] = None
    sortBy: Optional[str] = None
    sortOrder: Optional[str] = "desc"
