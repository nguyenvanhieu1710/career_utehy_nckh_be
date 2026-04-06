from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete, update
from fastapi import HTTPException, status
import math

from app.models.cv_template import CVTemplate  # Import model đã viết ở bước trước
from app.core.perms import require_permission

class CVTemplateService:
    
    @staticmethod
    async def get_templates(filters, db: AsyncSession):
        """
        Lấy danh sách template có phân trang và lọc theo category/status
        """
        try:
            query = select(CVTemplate)
            
            # Filter theo keyword
            if filters.searchKeyword:
                query = query.where(CVTemplate.name.ilike(f"%{filters.searchKeyword}%"))
            
            # Filter theo category
            if hasattr(filters, 'category') and filters.category and filters.category != "all":
                query = query.where(CVTemplate.category == filters.category)
            
            # Count tổng số bản ghi
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Pagination
            page = filters.page or 1
            row = filters.row or 10
            query = query.offset((page - 1) * row).limit(row)
            
            result = await db.execute(query)
            templates = result.scalars().all()
            
            return {
                "total": total,
                "page": page,
                "max_page": math.ceil(total / row) if total > 0 else 1,
                "data": templates
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    @require_permission(["cv_template.create"])
    async def create_template(user_perms: list[str], data, db: AsyncSession):
        """
        Tạo mới một mẫu CV
        """
        try:
            new_template = CVTemplate(
                name=data.name,
                category=data.category,
                default_title=data.default_title,
                default_subtitle=data.default_subtitle,
                primary_color=data.primary_color,
                default_sections=data.default_sections,
                design_data=data.design_data
            )
            db.add(new_template)
            await db.commit()
            await db.refresh(new_template)
            return {"status": "success", "data": new_template}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    @require_permission(["cv_template.update"])
    async def update_template_design(template_id: str, data, db: AsyncSession):
        """
        Cập nhật riêng phần thiết kế (Kéo thả từ Canvas) và ảnh Thumbnail
        """
        try:
            result = await db.execute(select(CVTemplate).where(CVTemplate.id == template_id))
            template = result.scalar_one_or_none()
            
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Cập nhật các trường liên quan đến thiết kế
            if hasattr(data, 'design_data'):
                template.design_data = data.design_data
            if hasattr(data, 'thumbnail'):
                template.thumbnail = data.thumbnail
            if hasattr(data, 'primary_color'):
                template.primary_color = data.primary_color
                
            await db.commit()
            return {"status": "success", "message": "Design updated successfully"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    @require_permission(["cv_template.create"])
    async def clone_template(template_id: str, db: AsyncSession):
        """
        Nhân bản một mẫu CV có sẵn
        """
        try:
            result = await db.execute(select(CVTemplate).where(CVTemplate.id == template_id))
            original = result.scalar_one_or_none()
            
            if not original:
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Tạo bản sao
            cloned_template = CVTemplate(
                name=f"{original.name} (Copy)",
                category=original.category,
                thumbnail=original.thumbnail,
                default_title=original.default_title,
                default_subtitle=original.default_subtitle,
                primary_color=original.primary_color,
                default_sections=original.default_sections,
                design_data=original.design_data,
                is_active=False # Mặc định bản copy ở trạng thái nháp
            )
            
            db.add(cloned_template)
            await db.commit()
            return {"status": "success", "data": cloned_template}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    @require_permission(["cv_template.delete"])
    async def delete_template(template_id: str, db: AsyncSession):
        """
        Xóa template
        """
        try:
            await db.execute(delete(CVTemplate).where(CVTemplate.id == template_id))
            await db.commit()
            return {"status": "success", "message": "Template deleted"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))