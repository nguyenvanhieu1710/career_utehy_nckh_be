from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel as BM
from typing import Optional


class CVUploaded(BaseModel):
    __tablename__ = 'cv_uploaded'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    
    # Relationships
    user = relationship('Users', back_populates='cv_uploaded')

class CVUploadedSave(BM):
    id: Optional[str] = None
    name: str

