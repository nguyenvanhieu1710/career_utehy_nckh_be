from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.category import Category, CategoryCreate, CategoryUpdate
from app.schemas import get_schema
from app.core.perms import require_permission
from app.services.upload_service import upload_service
import math
import os


@require_permission(["category.create"])
async def create_category(user_perms: list[str], data: CategoryCreate, db: AsyncSession):
    """
    Create a new category
    """
    try:
        # Check if category name already exists
        result = await db.execute(select(Category).where(Category.name == data.name))
        existing_category = result.scalar_one_or_none()
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name already exists"
            )
        
        # Create new category
        print(f"🔧 Creating category with data: name='{data.name}', description='{data.description}', avatar_url='{data.avatar_url}'")
        new_category = Category(
            name=data.name,
            description=data.description,
            avatar_url=data.avatar_url
        )
        print(f"🔧 Category instance created: {new_category}")
        db.add(new_category)
        print("🔧 Category added to session, attempting commit...")
        await db.commit()
        print("🔧 Commit successful, refreshing...")
        await db.refresh(new_category)
        print(f"🔧 Category refreshed: {new_category.id}")
        
        return {
            "status": "success",
            "message": "Category created successfully",
            "data": new_category
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@require_permission(["category.list"])
async def get_all_categories(user_perms: list[str], filters: get_schema.GetSchema, db: AsyncSession):
    """
    Get all categories with pagination and search
    """
    base_stmt = select(Category)
    
    # Filter out deleted categories (soft delete) - allow NULL values for backward compatibility
    base_stmt = base_stmt.where((Category.action_status != "deleted") | (Category.action_status.is_(None)))

    if filters.id:
        base_stmt = base_stmt.where(Category.id == filters.id)

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            (Category.name.ilike(keyword)) |
            (Category.description.ilike(keyword))
        )

    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    
    # Count total records
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    # Get paginated data
    result = await db.execute(base_stmt.offset(offset).limit(row))
    data = result.unique().scalars().all()

    max_page = math.ceil(total / row) if row > 0 else 1

    return {
        "total": total,
        "page": page,
        "max_page": max_page,
        "row": row,
        "data": data
    }


@require_permission(["category.read"])
async def get_category_by_id(user_perms: list[str], category_id: str, db: AsyncSession):
    """
    Get category by ID
    """
    result = await db.execute(select(Category).where(
        (Category.id == category_id) & 
        ((Category.action_status != "deleted") | (Category.action_status.is_(None)))
    ))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category


@require_permission(["category.update"])
async def update_category(user_perms: list[str], category_id: str, data: CategoryUpdate, db: AsyncSession):
    """
    Update category by ID with avatar cleanup
    """
    result = await db.execute(select(Category).where(
        (Category.id == category_id) & 
        ((Category.action_status != "deleted") | (Category.action_status.is_(None)))
    ))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if new name already exists (if name is being changed)
    if data.name and data.name != category.name:
        check_result = await db.execute(select(Category).where(Category.name == data.name))
        existing_category = check_result.scalar_one_or_none()
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name already exists"
            )
    
    # Handle avatar cleanup if avatar_url is being changed
    old_avatar_url = category.avatar_url
    cleanup_old_avatar = False
    
    if data.avatar_url is not None and data.avatar_url != old_avatar_url:
        cleanup_old_avatar = True
        print(f"🔄 Avatar change detected: '{old_avatar_url}' -> '{data.avatar_url}'")
    
    # Update fields
    if data.name:
        category.name = data.name
    if data.description is not None:  # Allow empty string to clear description
        category.description = data.description
    if data.avatar_url is not None:  # Allow empty string to clear avatar_url
        category.avatar_url = data.avatar_url

    await db.commit()
    await db.refresh(category)
    
    # Cleanup old avatar file after successful database update
    if cleanup_old_avatar and old_avatar_url:
        try:
            # Extract file path from URL (remove /uploads/ prefix)
            if old_avatar_url.startswith('/uploads/'):
                old_file_path = old_avatar_url[9:]  # Remove '/uploads/' prefix
                full_old_path = os.path.join(upload_service.base_upload_dir, old_file_path)
                
                if os.path.exists(full_old_path):
                    success = upload_service.delete_file(full_old_path)
                    if success:
                        print(f"✅ Old avatar deleted: {full_old_path}")
                    else:
                        print(f"⚠️ Failed to delete old avatar: {full_old_path}")
                else:
                    print(f"⚠️ Old avatar file not found: {full_old_path}")
        except Exception as e:
            print(f"⚠️ Error cleaning up old avatar: {str(e)}")
            # Don't fail the update if cleanup fails
    
    return {
        "status": "success",
        "message": "Category updated successfully",
        "data": category
    }


@require_permission(["category.delete"])
async def delete_category(user_perms: list[str], category_id: str, db: AsyncSession):
    """
    Soft delete category by ID with avatar cleanup
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Store avatar URL for cleanup
    avatar_url = category.avatar_url
    
    # Soft delete - change action_status to "deleted"
    category.action_status = "deleted"
    await db.commit()
    await db.refresh(category)
    
    # Cleanup avatar file after successful soft delete
    if avatar_url:
        try:
            # Extract file path from URL (remove /uploads/ prefix)
            if avatar_url.startswith('/uploads/'):
                file_path = avatar_url[9:]  # Remove '/uploads/' prefix
                full_path = os.path.join(upload_service.base_upload_dir, file_path)
                
                if os.path.exists(full_path):
                    success = upload_service.delete_file(full_path)
                    if success:
                        print(f"✅ Avatar deleted with category: {full_path}")
                    else:
                        print(f"⚠️ Failed to delete avatar: {full_path}")
                else:
                    print(f"⚠️ Avatar file not found: {full_path}")
        except Exception as e:
            print(f"⚠️ Error cleaning up avatar on delete: {str(e)}")
            # Don't fail the delete if cleanup fails
    
    return {
        "status": "success", 
        "message": "Category deleted successfully"
    }


# Helper function to get default avatar URL
def get_default_avatar_url() -> str:
    """
    Get default avatar URL for categories without custom avatar
    """
    return "/uploads/defaults/category-default.png"


# Helper function to validate avatar URL
def validate_avatar_url(avatar_url: str) -> bool:
    """
    Validate that avatar URL is from our upload system
    """
    if not avatar_url:
        return True  # Empty is valid
    
    # Must start with /uploads/ and be for categories
    if not avatar_url.startswith('/uploads/categories/'):
        return False
    
    # Extract file path and check if file exists
    file_path = avatar_url[9:]  # Remove '/uploads/' prefix
    full_path = os.path.join(upload_service.base_upload_dir, file_path)
    
    return os.path.exists(full_path) and os.path.isfile(full_path)