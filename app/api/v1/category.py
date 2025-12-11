from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import category_service, user_service
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
        print("=" * 60)
        print("📥 GET CATEGORIES REQUEST")
        print(f"User ID: {user_id}")
        print(f"Filters: {filters}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await category_service.get_all_categories(user_perms=perms, filters=filters, db=db)
        print(f"✅ Success: Found {result.get('total', 0)} categories")
        print("=" * 60)
        return result
    except PermissionError as e:
        print(f"❌ Permission Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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