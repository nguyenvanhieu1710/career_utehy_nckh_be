import os
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import aiofiles
from pathlib import Path


class UploadService:
    """
    Service for handling file uploads with organized directory structure
    """
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 
        'image/gif', 'image/webp'
    }
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Valid file types for directory organization
    VALID_FILE_TYPES = {
        'users', 'categories', 'jobs', 'companies', 'cv'
    }
    
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_upload_dir = base_upload_dir
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Ensure base upload directory exists"""
        os.makedirs(self.base_upload_dir, exist_ok=True)
    

    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename with original extension"""
        # Get file extension
        file_ext = Path(original_filename).suffix.lower()
        
        # Generate unique name
        unique_id = str(uuid.uuid4())[:8]  # First 8 chars of UUID
        timestamp = str(int(datetime.now().timestamp()))[-6:]  # Last 6 digits of timestamp
        
        # Clean original name (remove extension and special chars)
        clean_name = Path(original_filename).stem
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in ('-', '_'))[:20]
        
        return f"{clean_name}-{unique_id}-{timestamp}{file_ext}"
    
    def _validate_file_type(self, file: UploadFile) -> bool:
        """Validate file type by extension and MIME type"""
        # Check file extension
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False
        
        # Check MIME type
        if file.content_type not in self.ALLOWED_MIME_TYPES:
            return False
        
        return True
    
    def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size"""
        return file_size <= self.MAX_FILE_SIZE
    
    def _get_upload_directory(self, file_type: str) -> str:
        """Get upload directory path for specific file type"""
        if file_type not in self.VALID_FILE_TYPES:
            raise ValueError(f"Invalid file type. Must be one of: {', '.join(self.VALID_FILE_TYPES)}")
        
        upload_dir = os.path.join(self.base_upload_dir, file_type)
        
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        return upload_dir
    
    def _optimize_image(self, file_path: str, max_width: int = 1200, quality: int = 85):
        """Optimize image by resizing and compressing"""
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize if image is too large
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(file_path, optimize=True, quality=quality)
                
        except Exception as e:
            # Continue without optimization if it fails
            pass
    
    async def upload_single_file(
        self, 
        file: UploadFile, 
        file_type: str,
        optimize: bool = True
    ) -> dict:
        """
        Upload a single file
        
        Args:
            file: The uploaded file
            file_type: Type of file (users, categories, jobs, etc.)
            optimize: Whether to optimize the image
            
        Returns:
            dict: Upload result with file info
        """
        try:
            # Validate file type
            if not self._validate_file_type(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
                )
            
            # Read file content to check size
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate file size
            if not self._validate_file_size(file_size):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            # Reset file pointer
            await file.seek(0)
            
            # Get upload directory
            upload_dir = self._get_upload_directory(file_type)
            
            # Generate unique filename
            unique_filename = self._generate_unique_filename(file.filename or "unknown")
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Optimize image if requested
            if optimize:
                self._optimize_image(file_path)
            
            # Generate URL path (relative to uploads directory)
            relative_path = os.path.relpath(file_path, self.base_upload_dir)
            file_url = f"/uploads/{relative_path.replace(os.sep, '/')}"
            
            return {
                "status": "success",
                "file_url": file_url,
                "file_path": file_path,
                "relative_path": relative_path,
                "original_name": file.filename,
                "file_size": file_size,
                "file_type": file_type,
                "upload_date": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
    
    async def upload_multiple_files(
        self, 
        files: List[UploadFile], 
        file_type: str,
        optimize: bool = True
    ) -> dict:
        """
        Upload multiple files
        
        Args:
            files: List of uploaded files
            file_type: Type of files (users, categories, jobs, etc.)
            optimize: Whether to optimize the images
            
        Returns:
            dict: Upload results with file info list
        """
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        if len(files) > 10:  # Limit to 10 files per request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many files. Maximum 10 files per request"
            )
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                result = await self.upload_single_file(file, file_type, optimize)
                uploaded_files.append(result)
            except HTTPException as e:
                failed_files.append({
                    "filename": file.filename,
                    "error": e.detail
                })
        
        return {
            "status": "success" if not failed_files else "partial_success",
            "uploaded_files": uploaded_files,
            "failed_files": failed_files,
            "total_uploaded": len(uploaded_files),
            "total_failed": len(failed_files)
        }
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from the filesystem
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict: File information or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            relative_path = os.path.relpath(file_path, self.base_upload_dir)
            file_url = f"/uploads/{relative_path.replace(os.sep, '/')}"
            
            return {
                "file_path": file_path,
                "file_url": file_url,
                "relative_path": relative_path,
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            return None


# Global instance
upload_service = UploadService()