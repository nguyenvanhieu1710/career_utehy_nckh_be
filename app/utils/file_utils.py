import os
import re
import hashlib
import mimetypes
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image, ImageOps
import magic
from datetime import datetime


class FileUtils:
    """
    Utility class for file operations, validation, and optimization
    """
    
    # Dangerous file extensions that should never be allowed
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.php', '.asp', '.aspx', '.jsp', '.py', '.pl', '.sh', '.ps1'
    }
    
    # Image file extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    
    # Maximum filename length
    MAX_FILENAME_LENGTH = 255
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
        """
        Sanitize filename to prevent security issues and filesystem problems
        
        Args:
            filename: Original filename
            max_length: Maximum allowed filename length
            
        Returns:
            str: Sanitized filename
        """
        if not filename:
            return "unnamed_file"
        
        # Get file extension
        path = Path(filename)
        name = path.stem
        ext = path.suffix.lower()
        
        # Remove or replace dangerous characters
        # Keep only alphanumeric, hyphens, underscores, dots, and spaces
        name = re.sub(r'[^\w\s\-_.]', '', name)
        
        # Replace multiple spaces/underscores with single ones
        name = re.sub(r'[\s_]+', '_', name)
        
        # Remove leading/trailing spaces and dots
        name = name.strip(' ._')
        
        # Ensure name is not empty
        if not name:
            name = "file"
        
        # Truncate if too long (accounting for extension)
        max_name_length = max_length - len(ext)
        if len(name) > max_name_length:
            name = name[:max_name_length]
        
        return f"{name}{ext}"
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
        """
        Validate file extension against allowed list
        
        Args:
            filename: Filename to validate
            allowed_extensions: Set of allowed extensions (with dots)
            
        Returns:
            bool: True if extension is allowed
        """
        if not filename:
            return False
        
        ext = Path(filename).suffix.lower()
        
        # Check if extension is dangerous
        if ext in FileUtils.DANGEROUS_EXTENSIONS:
            return False
        
        # Check if extension is in allowed list
        return ext in allowed_extensions
    
    @staticmethod
    def validate_mime_type(file_path: str, allowed_mime_types: set) -> bool:
        """
        Validate MIME type using python-magic (more reliable than content-type header)
        
        Args:
            file_path: Path to file
            allowed_mime_types: Set of allowed MIME types
            
        Returns:
            bool: True if MIME type is allowed
        """
        try:
            # Use python-magic to detect actual file type
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type in allowed_mime_types
        except Exception:
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type in allowed_mime_types if mime_type else False
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'md5') -> str:
        """
        Calculate file hash for duplicate detection
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha1, sha256)
            
        Returns:
            str: File hash
        """
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def get_image_info(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed image information
        
        Args:
            file_path: Path to image file
            
        Returns:
            dict: Image information or None if not an image
        """
        try:
            with Image.open(file_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
                    'is_animated': getattr(img, 'is_animated', False),
                    'n_frames': getattr(img, 'n_frames', 1)
                }
        except Exception:
            return None
    
    @staticmethod
    def optimize_image(
        input_path: str,
        output_path: Optional[str] = None,
        max_width: int = 1200,
        max_height: int = 1200,
        quality: int = 85,
        format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize image by resizing and compressing
        
        Args:
            input_path: Path to input image
            output_path: Path for output (None = overwrite input)
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            quality: JPEG quality (1-100)
            format: Output format (None = keep original)
            
        Returns:
            dict: Optimization results
        """
        if output_path is None:
            output_path = input_path
        
        original_size = os.path.getsize(input_path)
        
        try:
            with Image.open(input_path) as img:
                original_format = img.format
                original_dimensions = img.size
                
                # Convert RGBA/P to RGB for better compatibility
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                    img = background
                
                # Auto-orient image based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                # Resize if image is too large
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Determine output format
                output_format = format or original_format
                if output_format not in ('JPEG', 'PNG', 'WEBP'):
                    output_format = 'JPEG'
                
                # Save with optimization
                save_kwargs = {'optimize': True}
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality
                elif output_format == 'PNG':
                    save_kwargs['compress_level'] = 6
                elif output_format == 'WEBP':
                    save_kwargs['quality'] = quality
                
                img.save(output_path, format=output_format, **save_kwargs)
                
                optimized_size = os.path.getsize(output_path)
                
                return {
                    'success': True,
                    'original_size': original_size,
                    'optimized_size': optimized_size,
                    'size_reduction': original_size - optimized_size,
                    'size_reduction_percent': round((1 - optimized_size / original_size) * 100, 2),
                    'original_dimensions': original_dimensions,
                    'final_dimensions': img.size,
                    'original_format': original_format,
                    'final_format': output_format
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_size': original_size
            }
    
    @staticmethod
    def create_thumbnail(
        input_path: str,
        output_path: str,
        size: Tuple[int, int] = (150, 150),
        quality: int = 80
    ) -> bool:
        """
        Create thumbnail image
        
        Args:
            input_path: Path to input image
            output_path: Path for thumbnail
            size: Thumbnail size (width, height)
            quality: JPEG quality
            
        Returns:
            bool: True if successful
        """
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                    img = background
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                return True
                
        except Exception as e:
            return False
    
    @staticmethod
    def clean_old_files(
        directory: str,
        max_age_days: int = 30,
        file_pattern: str = "*",
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean old files from directory
        
        Args:
            directory: Directory to clean
            max_age_days: Maximum file age in days
            file_pattern: File pattern to match
            dry_run: If True, only report what would be deleted
            
        Returns:
            dict: Cleanup results
        """
        if not os.path.exists(directory):
            return {'error': 'Directory does not exist'}
        
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        files_to_delete = []
        total_size = 0
        
        try:
            for file_path in Path(directory).rglob(file_pattern):
                if file_path.is_file():
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_time:
                        files_to_delete.append({
                            'path': str(file_path),
                            'size': file_stat.st_size,
                            'modified': datetime.fromtimestamp(file_stat.st_mtime)
                        })
                        total_size += file_stat.st_size
            
            deleted_count = 0
            if not dry_run:
                for file_info in files_to_delete:
                    try:
                        os.remove(file_info['path'])
                        deleted_count += 1
                    except Exception as e:
                        pass
            
            return {
                'success': True,
                'files_found': len(files_to_delete),
                'files_deleted': deleted_count if not dry_run else 0,
                'total_size_freed': total_size if not dry_run else 0,
                'dry_run': dry_run,
                'files': files_to_delete[:10]  # Show first 10 files
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def ensure_directory_exists(directory: str, mode: int = 0o755) -> bool:
        """
        Ensure directory exists, create if necessary
        
        Args:
            directory: Directory path
            mode: Directory permissions
            
        Returns:
            bool: True if directory exists or was created
        """
        try:
            os.makedirs(directory, mode=mode, exist_ok=True)
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def get_directory_size(directory: str) -> Dict[str, Any]:
        """
        Calculate total size of directory
        
        Args:
            directory: Directory path
            
        Returns:
            dict: Directory size information
        """
        if not os.path.exists(directory):
            return {'error': 'Directory does not exist'}
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                dir_count += len(dirnames)
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except (OSError, IOError):
                        continue
            
            return {
                'success': True,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'directory_count': dir_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global utility instance
file_utils = FileUtils()