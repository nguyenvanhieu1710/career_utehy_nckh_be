from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services.cv_template_service import CVTemplateService
from app.schemas.get_schema import GetSchema 
from app.models.cv_template import CVTemplateSave
from app.utils import auth
from typing import List

from app.services import user_service

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/get-all")
async def get_templates(
    filters: GetSchema, 
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách template (Admin/User đều có thể gọi tùy logic phân quyền của bạn)
    """
    return await CVTemplateService.get_templates(filters, db)

@router.get("/{template_id}")
async def get_template_by_id(
    template_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy chi tiết 1 template để đổ vào Canvas
    """
    from app.models.cv_template import CVTemplate
    from sqlalchemy.future import select
    
    result = await db.execute(select(CVTemplate).where(CVTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template không tồn tại")
    return {"status": "success", "data": template}

@router.post("/create")
async def create_template(
    data: CVTemplateSave, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Tạo template mới
    """
    perms = await user_service.get_user_permissions(user_id=user_id, db=db)
    return await CVTemplateService.create_template(user_perms=perms, data=data, db=db)

@router.put("/update-design/{template_id}")
async def update_template_design(
    template_id: str, 
    data: CVTemplateSave, 
    perms: List[str] = Depends(auth.get_current_user_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật thiết kế từ trang Canvas kéo thả
    """
    # Lưu ý: CVTemplateSave nên có optional các trường design_data và thumbnail
    return await CVTemplateService.update_template_design(template_id, data, db)

@router.post("/clone/{template_id}")
async def clone_template(
    template_id: str, 
    perms: List[str] = Depends(auth.get_current_user_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Nhân bản mẫu CV
    """
    return await CVTemplateService.clone_template(template_id, db)

@router.delete("/delete/{template_id}")
async def delete_template(
    template_id: str, 
    perms: List[str] = Depends(auth.get_current_user_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa mẫu CV
    """
    return await CVTemplateService.delete_template(template_id, db)