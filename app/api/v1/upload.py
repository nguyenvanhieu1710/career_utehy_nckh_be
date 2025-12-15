from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
from pathlib import Path

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
        print("=" * 60)
        print("📤 SINGLE FILE UPLOAD REQUEST")
        print(f"User ID: {user_id}")
        print(f"File type: {file_type}")
        print(f"File name: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"Optimize: {optimize}")
        
        # Check user permissions (optional - you can add specific permissions)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        # Upload file
        result = await upload_service.upload_single_file(
            file=file,
            file_type=file_type.value,
            optimize=optimize
        )
        
        print(f"✅ Upload successful: {result['file_url']}")
        print("=" * 60)
        
        return SingleUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print("=" * 60)
        print("📤 MULTIPLE FILES UPLOAD REQUEST")
        print(f"User ID: {user_id}")
        print(f"File type: {file_type}")
        print(f"Number of files: {len(files)}")
        print(f"File names: {[f.filename for f in files]}")
        print(f"Optimize: {optimize}")
        
        # Check user permissions (optional)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        # Upload files
        result = await upload_service.upload_multiple_files(
            files=files,
            file_type=file_type.value,
            optimize=optimize
        )
        
        print(f"✅ Upload completed: {result['total_uploaded']} success, {result['total_failed']} failed")
        print("=" * 60)
        
        return MultipleUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print(f"📋 FILE INFO REQUEST: {file_path} by user {user_id}")
        
        # Construct full path
        full_path = os.path.join(upload_service.base_upload_dir, file_path)
        
        # Get file info
        file_info = upload_service.get_file_info(full_path)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        print(f"✅ File info retrieved: {file_info['file_size']} bytes")
        
        return FileInfoResponse(**file_info)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ File Info Error: {type(e).__name__}: {str(e)}")
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
        print(f"🗑️ DELETE FILE REQUEST: {file_path} by user {user_id}")
        
        # Check user permissions (you might want to add specific delete permissions)
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
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
            print(f"✅ File deleted successfully: {file_path}")
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
        print(f"❌ Delete Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/serve/{file_path:path}")
async def serve_file(
    file_path: str,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(auth.verify_token_user_optional)  # Optional auth for public files
):
    """
    Serve uploaded files (static file serving)
    
    - **file_path**: Relative path from uploads directory
    
    Returns the actual file for display/download
    """
    try:
        # Construct full path
        full_path = os.path.join(upload_service.base_upload_dir, file_path)
        
        # Security check: ensure path is within uploads directory
        uploads_dir = os.path.abspath(upload_service.base_upload_dir)
        requested_path = os.path.abspath(full_path)
        
        if not requested_path.startswith(uploads_dir):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check if it's actually a file (not directory)
        if not os.path.isfile(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not a file"
            )
        
        # Get file extension for media type
        file_extension = Path(full_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        print(f"📁 Serving file: {file_path} (type: {media_type})")
        
        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=os.path.basename(full_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Serve File Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve file: {str(e)}"
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
        print(f"❌ Config Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def upload_health_check():
    """
    Health check for upload service
    
    Returns service status and upload directory info
    """
    try:
        uploads_dir = upload_service.base_upload_dir
        uploads_exists = os.path.exists(uploads_dir)
        uploads_writable = os.access(uploads_dir, os.W_OK) if uploads_exists else False
        
        return {
            "status": "healthy" if uploads_exists and uploads_writable else "unhealthy",
            "uploads_directory": uploads_dir,
            "directory_exists": uploads_exists,
            "directory_writable": uploads_writable,
            "max_file_size": f"{upload_service.MAX_FILE_SIZE // (1024*1024)}MB",
            "allowed_types": list(upload_service.ALLOWED_EXTENSIONS)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }