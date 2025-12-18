"""
Entity Status Management Constants
"""
from enum import Enum
from typing import List, Dict, Any

class EntityStatus(str, Enum):
    """Entity status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    DELETED = "deleted"

# Valid status values
VALID_STATUSES = [status.value for status in EntityStatus]

# Status display information
STATUS_INFO = {
    EntityStatus.ACTIVE: {
        "label": "Hoạt động",
        "color": "green",
        "description": "Đang hoạt động bình thường"
    },
    EntityStatus.INACTIVE: {
        "label": "Không hoạt động",
        "color": "yellow", 
        "description": "Tạm thời không hoạt động"
    },
    EntityStatus.DELETED: {
        "label": "Đã xóa",
        "color": "red",
        "description": "Đã bị xóa khỏi hệ thống"
    }
}

def get_status_options() -> List[Dict[str, Any]]:
    """Get all available status options"""
    return [
        {
            "value": status.value,
            "label": STATUS_INFO[status]["label"],
            "color": STATUS_INFO[status]["color"],
            "description": STATUS_INFO[status]["description"]
        }
        for status in EntityStatus
    ]

def is_valid_status(status: str) -> bool:
    """Check if status is valid"""
    return status in VALID_STATUSES

def get_default_status() -> str:
    """Get default status for new entities"""
    return EntityStatus.ACTIVE.value