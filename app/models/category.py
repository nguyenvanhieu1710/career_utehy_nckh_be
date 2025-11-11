from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base_model import BaseModel

class Category(BaseModel):
    __tablename__ = 'categories'
    
    name = Column(String(100), nullable=False)
    parent_id = Column(String(36), ForeignKey('categories.id'), nullable=True)
    description = Column(Text)
    
    # Self-referential relationship for parent-child categories
    parent = relationship('Category', remote_side='Category.id', backref='subcategories')
