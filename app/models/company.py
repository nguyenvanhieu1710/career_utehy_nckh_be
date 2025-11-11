from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class Company(BaseModel):
    __tablename__ = 'companies'
    
    name = Column(String(200), nullable=False)
    slug = Column(String(255), unique=True)
    logo_url = Column(String(255))
    website = Column(String(255))
    address = Column(String(255))
    description = Column(Text)
    industry = Column(String(100))
    sub_industries = Column(JSON)
    size = Column(String(50))
    locations = Column(JSON)
    email = Column(String(100))
    support_email = Column(String(100))
    phone = Column(String(20))
    
    # Relationships
    jobs = relationship('Job', back_populates='company')
