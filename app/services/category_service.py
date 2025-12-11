from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.category import Category, CategoryCreate, CategoryUpdate
from app.schemas import get_schema
from app.core.perms import require_permission
import math


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
        print(f"🔧 Creating category with data: name='{data.name}', description='{data.description}'")
        new_category = Category(
            name=data.name,
            description=data.description
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
    Update category by ID
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
    
    # Update fields
    if data.name:
        category.name = data.name
    if data.description is not None:  # Allow empty string to clear description
        category.description = data.description

    await db.commit()
    await db.refresh(category)
    
    return {
        "status": "success",
        "message": "Category updated successfully",
        "data": category
    }


@require_permission(["category.delete"])
async def delete_category(user_perms: list[str], category_id: str, db: AsyncSession):
    """
    Soft delete category by ID
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Soft delete - change action_status to "deleted"
    category.action_status = "deleted"
    await db.commit()
    await db.refresh(category)
    
    return {
        "status": "success", 
        "message": "Category deleted successfully"
    }