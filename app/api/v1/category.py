from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import category_service, user_service
from app.services.upload_service import upload_service
from app.models.category import CategoryCreate, CategoryUpdate
from app.schemas import get_schema
from app.utils import auth

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/get-categories")
async def get_categories(
    filters: get_schema.GetSchema,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all categories with pagination and search
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await category_service.get_all_categories(user_perms=perms, filters=filters, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/get-category/{category_id}")
async def get_category_detail(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get category by ID
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await category_service.get_category_by_id(user_perms=perms, category_id=category_id, db=db)
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/create-category")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Create a new category
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await category_service.create_category(user_perms=perms, data=data, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/update-category/{category_id}")
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Update category by ID
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await category_service.update_category(user_perms=perms, category_id=category_id, data=data, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/delete-category/{category_id}")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Delete category by ID (soft delete)
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await category_service.delete_category(user_perms=perms, category_id=category_id, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upload-avatar/{category_id}")
async def upload_category_avatar(
    category_id: str,
    file: UploadFile = File(..., description="Avatar image file"),
    optimize: bool = Form(True, description="Whether to optimize the uploaded image"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Upload avatar for a specific category
    
    - **category_id**: ID of the category to update
    - **file**: Avatar image file (jpg, jpeg, png, gif, webp)
    - **optimize**: Whether to optimize image (resize + compress)
    
    Returns uploaded avatar information and updates category
    """
    try:
        # Check user permissions
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Check if category exists
        category = await category_service.get_category_by_id(user_perms=perms, category_id=category_id, db=db)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Upload avatar file
        upload_result = await upload_service.upload_single_file(
            file=file,
            file_type="categories",
            optimize=optimize
        )
        
        # Update category with new avatar URL
        update_data = CategoryUpdate(avatar_url=upload_result['file_url'])
        updated_category = await category_service.update_category(
            user_perms=perms,
            category_id=category_id,
            data=update_data,
            db=db
        )
        
        return {
            "status": "success",
            "message": "Category avatar uploaded successfully",
            "avatar_info": upload_result,
            "category": updated_category["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar upload failed: {str(e)}"
        )


@router.delete("/remove-avatar/{category_id}")
async def remove_category_avatar(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Remove avatar from a specific category
    
    - **category_id**: ID of the category to update
    
    Returns success message and updates category
    """
    try:
        # Check user permissions
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Check if category exists
        category = await category_service.get_category_by_id(user_perms=perms, category_id=category_id, db=db)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Update category to remove avatar (set to None/empty)
        update_data = CategoryUpdate(avatar_url="")
        updated_category = await category_service.update_category(
            user_perms=perms,
            category_id=category_id,
            data=update_data,
            db=db
        )
        
        return {
            "status": "success",
            "message": "Category avatar removed successfully",
            "category": updated_category["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove avatar: {str(e)}"
        )