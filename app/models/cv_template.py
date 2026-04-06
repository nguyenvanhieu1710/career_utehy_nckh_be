from sqlalchemy import Column, String, Text, JSON, Boolean, Integer
from .base_model import BaseModel
from pydantic import BaseModel as BM
from typing import Optional, Any, Dict, List

class CVTemplate(BaseModel):
    __tablename__ = 'cv_templates'
    
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Dữ liệu nội dung mặc định (giống CVProfile)
    default_title = Column(String(100), nullable=True)
    default_subtitle = Column(String(100), nullable=True)
    primary_color = Column(String(20), default="#1d7057ff")
    default_sections = Column(Text, nullable=False)
    
    design_data = Column(Text, nullable=False)

# Schema dùng cho việc tạo/cập nhật Template từ Admin
class CVTemplateSave(BM):
    id: Optional[str] = None
    name: str
    category: Optional[str] = "General"
    is_active: Optional[bool] = True
    
    # Nội dung mặc định
    default_title: Optional[str] = "Họ và Tên"
    default_subtitle: Optional[str] = "Vị trí ứng tuyển"
    primary_color: Optional[str] = "#1d7057ff"
    default_sections: str # JSON string của mảng Section
    
    # Cấu trúc layout kéo thả
    design_data: str

# Schema dùng cho Filter/Search ở trang quản lý
class CVTemplateFilter(BM):
    searchKeyword: Optional[str] = ""
    category: Optional[str] = None
    status: Optional[str] = None # active / inactive
    page: int = 1
    row: int = 10