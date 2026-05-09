from sqlalchemy import Column, String, Text, ForeignKey, JSON
from .base_model import BaseModel
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class SystemLog(BaseModel):
    __tablename__ = 'system_logs'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    action_type = Column(String(50), nullable=False)  # 'visit', 'action', 'login', 'error', etc.
    description = Column(Text)
    path = Column(String(255))
    method = Column(String(10))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    duration_ms = Column(Float)  # Request processing time in milliseconds
    metadata_json = Column(JSON)  # For additional context (e.g., request params, error stack)
    
    # Relationships
    user = relationship('Users', backref='system_logs')

    def __repr__(self):
        return f"<SystemLog(id={self.id}, type={self.action_type}, path={self.path})>"
