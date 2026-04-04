"""
Common API endpoints for shared resources
"""
from fastapi import APIRouter, Depends
from app.core.status import get_status_options
from app.utils import auth

router = APIRouter()

@router.get("/status-options")
async def get_available_status_options():
    """
    Get all available status options for entities
    No authentication required as this is basic system data
    """
    try:
        options = get_status_options()
        return {
            "status": "success",
            "data": options
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Failed to get status options: {str(e)}"
        }

@router.get("/status-options-auth")
async def get_available_status_options_with_auth(
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all available status options for entities (with authentication)
    """
    try:
        options = get_status_options()
        return {
            "status": "success",
            "data": options,
            "user_id": user_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get status options: {str(e)}"
        }