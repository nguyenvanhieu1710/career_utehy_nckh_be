from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os

from app.core.database import SessionLocal
from app.services import user_service
from app.services.upload_service import upload_service
from app.models.upload import (
    FileType, SingleUploadResponse, MultipleUploadResponse, 
    FileInfoResponse, DeleteFileResponse, ErrorResponse,
    UploadConfig
)
from app.utils import auth

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/single/{file_type}", response_model=SingleUploadResponse)
async def upload_single_file(
    file_type: FileType,
    file: UploadFile = File(..., description="Image file to upload"),
    optimize: bool = Form(True, description="Whether to optimize the uploaded image"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Upload a single image file
    
    - **file_type**: Category of file (users, categories, jobs, companies, cv)
    - **file**: Image file (jpg, jpeg, png, gif, webp)
    - **optimize**: Whether to optimize image (resize + compress)
    
    Returns uploaded file information including public URL
    """
    try:
        # Check user permissions (optional - you can add specific permissions)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Upload file
        result = await upload_service.upload_single_file(
            file=file,
            file_type=file_type.value,
            optimize=optimize
        )
        
        return SingleUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/multiple/{file_type}", response_model=MultipleUploadResponse)
async def upload_multiple_files(
    file_type: FileType,
    files: List[UploadFile] = File(..., description="Image files to upload (max 10)"),
    optimize: bool = Form(True, description="Whether to optimize the uploaded images"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Upload multiple image files
    
    - **file_type**: Category of files (users, categories, jobs, companies, cv)
    - **files**: List of image files (jpg, jpeg, png, gif, webp) - max 10 files
    - **optimize**: Whether to optimize images (resize + compress)
    
    Returns information about uploaded and failed files
    """
    try:
        # Check user permissions (optional)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Upload files
        result = await upload_service.upload_multiple_files(
            files=files,
            file_type=file_type.value,
            optimize=optimize
        )
        
        return MultipleUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/file-info")
async def get_file_info(
    file_path: str = Query(..., description="Relative path to the file from uploads directory"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get information about an uploaded file
    
    - **file_path**: Relative path from uploads directory (e.g., "categories/2024-12-11/tech-123.jpg")
    
    Returns file information including size, dates, and existence status
    """
    try:
        # Construct full path
        full_path = os.path.join(upload_service.base_upload_dir, file_path)
        
        # Get file info
        file_info = upload_service.get_file_info(full_path)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileInfoResponse(**file_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file info: {str(e)}"
        )


@router.delete("/file")
async def delete_file(
    file_path: str = Query(..., description="Relative path to the file from uploads directory"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Delete an uploaded file
    
    - **file_path**: Relative path from uploads directory (e.g., "categories/2024-12-11/tech-123.jpg")
    
    Returns deletion status
    """
    try:
        # Check user permissions (you might want to add specific delete permissions)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Construct full path
        full_path = os.path.join(upload_service.base_upload_dir, file_path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete file
        success = upload_service.delete_file(full_path)
        
        if success:
            return DeleteFileResponse(
                status="success",
                message="File deleted successfully",
                file_path=file_path
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/config", response_model=UploadConfig)
async def get_upload_config():
    """
    Get upload configuration and limits
    
    Returns current upload limits and allowed file types
    """
    try:
        config = UploadConfig(
            max_file_size=upload_service.MAX_FILE_SIZE,
            max_files_per_request=10,
            allowed_extensions=list(upload_service.ALLOWED_EXTENSIONS),
            allowed_mime_types=list(upload_service.ALLOWED_MIME_TYPES),
            valid_file_types=list(FileType),
            image_optimization={
                "enabled": True,
                "max_width": 1200,
                "quality": 85
            }
        )
        
        return config
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )