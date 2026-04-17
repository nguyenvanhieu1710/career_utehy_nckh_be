from typing import Optional
from app.schemas.get_schema import GetSchema

class JobFilterSchema(GetSchema):
    location: Optional[str] = None
    job_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    work_arrangement: Optional[str] = None
    experience_level: Optional[str] = None
    remote_allowed: Optional[bool] = None
