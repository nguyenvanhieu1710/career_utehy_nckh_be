from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status, UploadFile
import math
import os
from app.models.cv_uploaded import CVUploaded
from app.services.upload_service import upload_service
from app.schemas.get_schema import GetSchema

async def upload_cv(
    file: UploadFile,
    name: str,
    user_id: str,
    db: AsyncSession
):
    """
    Handle uploading a PDF CV and saving record to database
    """
    # Use upload_service to save the file
    # Note: optimize=False because it's a PDF, not an image
    try:
        upload_result = await upload_service.upload_single_file(
            file=file,
            file_type="cv",
            optimize=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )
    
    if upload_result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
    
    new_cv = CVUploaded(
        user_id=user_id,
        name=name or upload_result.get("original_name", "Uploaded CV"),
        file_path=upload_result.get("file_url") # Store URL path in file_path column
    )
    
    # We can store the absolute path in a temporary way or another column if needed for deletion
    # For simplicity and following project pattern, we store the URL
    
    db.add(new_cv)
    await db.commit()
    await db.refresh(new_cv)
    return new_cv

async def get_uploaded_cvs(
    user_id: str,
    filters: GetSchema,
    db: AsyncSession
):
    """
    List uploaded CVs for a specific user
    """
    base_stmt = select(CVUploaded).where(CVUploaded.user_id == user_id)
    
    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(CVUploaded.name.ilike(keyword))
        
    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    
    result = await db.execute(base_stmt.order_by(CVUploaded.created_at.desc()).offset(offset).limit(row))
    data = result.scalars().all()
    
    max_page = math.ceil(total / row) if row > 0 else 1
    
    return {
        "total": total,
        "page": page,
        "max_page": max_page,
        "row": row,
        "data": data
    }

async def delete_uploaded_cv(
    cv_id: str,
    user_id: str,
    db: AsyncSession
):
    """
    Delete an uploaded CV record and its physical file
    """
    result = await db.execute(
        select(CVUploaded).where(CVUploaded.id == cv_id).where(CVUploaded.user_id == user_id)
    )
    cv = result.scalar_one_or_none()
    
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded CV not found"
        )
    
    # Handle file deletion
    # Reconstruct absolute path from URL if possible
    # file_path in DB is like "/uploads/cv/filename.pdf"
    # base_upload_dir is "uploads"
    if cv.file_path:
        # Remove the leading "/uploads/" to get relative path
        rel_path = cv.file_path.replace("/uploads/", "")
        abs_path = os.path.join("uploads", rel_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    
    await db.delete(cv)
    await db.commit()
    return {"status": "success", "message": "Uploaded CV deleted successfully"}
