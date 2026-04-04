"""
Common API endpoints for shared resources
"""
from fastapi import APIRouter
from app.core.status import get_status_options

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