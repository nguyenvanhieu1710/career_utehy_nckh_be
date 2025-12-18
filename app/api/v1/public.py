from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services import category_service
from app.core.status import EntityStatus

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.get("/categories")
async def get_public_categories(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get active categories for public display (no authentication required)
    
    - **limit**: Maximum number of categories to return (default: 20, max: 50)
    
    Returns only active categories with basic information
    """
    try:
        print("=" * 60)
        print("📥 PUBLIC CATEGORIES REQUEST")
        print(f"Limit: {limit}")
        
        # Validate limit
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 20
        
        # Get active categories without permission check
        result = await category_service.get_public_categories(limit=limit, db=db)
        
        print(f"✅ Success: Found {len(result)} public categories")
        print("=" * 60)
        
        return {
            "status": "success",
            "data": result,
            "total": len(result)
        }
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch public categories"
        )


@router.get("/categories/{category_id}")
async def get_public_category_detail(
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get public category detail by ID (no authentication required)
    
    - **category_id**: ID of the category
    
    Returns category details if active
    """
    try:
        print(f"📥 PUBLIC CATEGORY DETAIL REQUEST: {category_id}")
        
        # Get category detail without permission check
        result = await category_service.get_public_category_by_id(category_id=category_id, db=db)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or not active"
            )
        
        print(f"✅ Success: Found public category {category_id}")
        
        return {
            "status": "success",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch category details"
        )