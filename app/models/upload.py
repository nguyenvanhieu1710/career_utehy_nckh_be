from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Enum for valid file types/categories"""
    USERS = "users"
    CATEGORIES = "categories"
    JOBS = "jobs"
    COMPANIES = "companies"
    CV = "cv"


class UploadedFileInfo(BaseModel):
    """Information about a single uploaded file"""
    status: Literal["success"] = "success"
    file_url: str = Field(..., description="Public URL to access the file")
    file_path: str = Field(..., description="Full file path on server")
    relative_path: str = Field(..., description="Relative path from uploads directory")
    original_name: Optional[str] = Field(None, description="Original filename")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    file_type: FileType = Field(..., description="Type/category of the file")
    upload_date: str = Field(..., description="Upload timestamp in ISO format")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FailedFileInfo(BaseModel):
    """Information about a failed file upload"""
    filename: Optional[str] = Field(None, description="Original filename")
    error: str = Field(..., description="Error message")


class SingleUploadResponse(BaseModel):
    """Response for single file upload"""
    status: Literal["success"] = "success"
    file_url: str = Field(..., description="Public URL to access the file")
    file_path: str = Field(..., description="Full file path on server")
    relative_path: str = Field(..., description="Relative path from uploads directory")
    original_name: Optional[str] = Field(None, description="Original filename")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    file_type: FileType = Field(..., description="Type/category of the file")
    upload_date: str = Field(..., description="Upload timestamp in ISO format")
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "status": "success",
                "file_url": "/uploads/categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "file_path": "uploads/categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "relative_path": "categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "original_name": "technology.jpg",
                "file_size": 245760,
                "file_type": "categories",
                "upload_date": "2024-12-11T10:30:45.123456"
            }
        }


class MultipleUploadResponse(BaseModel):
    """Response for multiple file upload"""
    status: Literal["success", "partial_success"] = Field(..., description="Overall upload status")
    uploaded_files: List[UploadedFileInfo] = Field(default_factory=list, description="Successfully uploaded files")
    failed_files: List[FailedFileInfo] = Field(default_factory=list, description="Failed file uploads")
    total_uploaded: int = Field(..., description="Number of successfully uploaded files", ge=0)
    total_failed: int = Field(..., description="Number of failed uploads", ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "uploaded_files": [
                    {
                        "status": "success",
                        "file_url": "/uploads/users/2024-12-11/avatar-a1b2c3d4-123456.jpg",
                        "file_path": "uploads/users/2024-12-11/avatar-a1b2c3d4-123456.jpg",
                        "relative_path": "users/2024-12-11/avatar-a1b2c3d4-123456.jpg",
                        "original_name": "avatar.jpg",
                        "file_size": 156789,
                        "file_type": "users",
                        "upload_date": "2024-12-11T10:30:45.123456"
                    }
                ],
                "failed_files": [],
                "total_uploaded": 1,
                "total_failed": 0
            }
        }


class FileInfoResponse(BaseModel):
    """Response for file information query"""
    file_path: str = Field(..., description="Full file path on server")
    file_url: str = Field(..., description="Public URL to access the file")
    relative_path: str = Field(..., description="Relative path from uploads directory")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    created_at: str = Field(..., description="File creation timestamp")
    modified_at: str = Field(..., description="File modification timestamp")
    exists: bool = Field(True, description="Whether the file exists")
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "uploads/categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "file_url": "/uploads/categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "relative_path": "categories/2024-12-11/tech-a1b2c3d4-123456.jpg",
                "file_size": 245760,
                "created_at": "2024-12-11T10:30:45.123456",
                "modified_at": "2024-12-11T10:30:45.123456",
                "exists": True
            }
        }


class DeleteFileResponse(BaseModel):
    """Response for file deletion"""
    status: Literal["success", "error"] = Field(..., description="Deletion status")
    message: str = Field(..., description="Status message")
    file_path: Optional[str] = Field(None, description="Path of the deleted file")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "File deleted successfully",
                "file_path": "uploads/categories/2024-12-11/tech-a1b2c3d4-123456.jpg"
            }
        }


class UploadValidationError(BaseModel):
    """Validation error response"""
    status: Literal["error"] = "error"
    error_type: str = Field(..., description="Type of validation error")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "error_type": "file_type_invalid",
                "message": "Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp",
                "details": {
                    "provided_type": ".pdf",
                    "allowed_types": [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                }
            }
        }


class UploadConfig(BaseModel):
    """Upload configuration and limits"""
    max_file_size: int = Field(5 * 1024 * 1024, description="Maximum file size in bytes")
    max_files_per_request: int = Field(10, description="Maximum files per upload request")
    allowed_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".webp"],
        description="Allowed file extensions"
    )
    allowed_mime_types: List[str] = Field(
        default=["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"],
        description="Allowed MIME types"
    )
    valid_file_types: List[FileType] = Field(
        default=[FileType.USERS, FileType.CATEGORIES, FileType.JOBS, FileType.COMPANIES, FileType.CV],
        description="Valid file type categories"
    )
    image_optimization: dict = Field(
        default={
            "enabled": True,
            "max_width": 1200,
            "quality": 85
        },
        description="Image optimization settings"
    )
    
    class Config:
        use_enum_values = True


# Request validation schemas
class UploadRequest(BaseModel):
    """Base upload request validation"""
    file_type: FileType = Field(..., description="Type/category for the uploaded file")
    optimize: bool = Field(True, description="Whether to optimize uploaded images")
    
    @validator('file_type')
    def validate_file_type(cls, v):
        if v not in FileType:
            raise ValueError(f"Invalid file type. Must be one of: {', '.join([ft.value for ft in FileType])}")
        return v
    
    class Config:
        use_enum_values = True


class SingleUploadRequest(UploadRequest):
    """Single file upload request validation"""
    pass


class MultipleUploadRequest(UploadRequest):
    """Multiple file upload request validation"""
    max_files: int = Field(10, description="Maximum number of files to upload", le=10, ge=1)


# Error response schemas
class ErrorResponse(BaseModel):
    """Generic error response"""
    status: Literal["error"] = "error"
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    details: Optional[dict] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "File upload failed",
                "error_code": "UPLOAD_FAILED",
                "details": {
                    "reason": "File size exceeds limit",
                    "max_size": "5MB",
                    "provided_size": "8MB"
                }
            }
        }


# Success response schemas
class SuccessResponse(BaseModel):
    """Generic success response"""
    status: Literal["success"] = "success"
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Additional response data")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {}
            }
        }