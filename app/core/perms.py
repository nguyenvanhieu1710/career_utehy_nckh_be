from enum import Enum
from typing import Optional, Union, List

class PermissionGroup(str, Enum):
    USER = "user"
    ROLE = "role"
    JOB = "job"
    COMPANY = "company"
    CATEGORY = "category"
    CRAWL_HISTORY = "crawl_history"
    CRAWLER_CONFIG = "crawler_config"
    CV_PROFILE = "cv_profile"
    DATA_SOURCE = "data_source"
    JOB_FAVORITE = "job_favorite"

PERMISSION_DEFINITIONS: dict[str, dict] = {
    # --- User ---
    "user.create":  {"group": PermissionGroup.USER, "label": "Tạo người dùng"},
    "user.read":    {"group": PermissionGroup.USER, "label": "Xem người dùng"},
    "user.update":  {"group": PermissionGroup.USER, "label": "Cập nhật người dùng"},
    "user.delete":  {"group": PermissionGroup.USER, "label": "Xóa người dùng"},
    "user.list":    {"group": PermissionGroup.USER, "label": "Danh sách người dùng"},

    # --- Role (User roles & Permissions management) ---
    "role.create":  {"group": PermissionGroup.ROLE, "label": "Tạo vai trò"},
    "role.read":    {"group": PermissionGroup.ROLE, "label": "Xem vai trò"},
    "role.update":  {"group": PermissionGroup.ROLE, "label": "Cập nhật vai trò"},
    "role.delete":  {"group": PermissionGroup.ROLE, "label": "Xóa vai trò"},

    # --- Job ---
    "job.create":   {"group": PermissionGroup.JOB, "label": "Tạo việc làm"},
    "job.read":     {"group": PermissionGroup.JOB, "label": "Xem việc làm"},
    "job.update":   {"group": PermissionGroup.JOB, "label": "Cập nhật việc làm"},
    "job.delete":   {"group": PermissionGroup.JOB, "label": "Xóa việc làm"},
    "job.list":     {"group": PermissionGroup.JOB, "label": "Danh sách việc làm"},
    "job.approve":  {"group": PermissionGroup.JOB, "label": "Duyệt việc làm"},
    "job.reject":   {"group": PermissionGroup.JOB, "label": "Từ chối việc làm"},

    # --- Company ---
    # "company.create": {"group": PermissionGroup.COMPANY, "label": "Tạo công ty"},
    # "company.read":   {"group": PermissionGroup.COMPANY, "label": "Xem công ty"},
    # "company.update": {"group": PermissionGroup.COMPANY, "label": "Cập nhật công ty"},
    # "company.delete": {"group": PermissionGroup.COMPANY, "label": "Xóa công ty"},
    # "company.list":   {"group": PermissionGroup.COMPANY, "label": "Danh sách công ty"},

    # --- Category ---
    "category.create": {"group": PermissionGroup.CATEGORY, "label": "Tạo danh mục"},
    "category.read":   {"group": PermissionGroup.CATEGORY, "label": "Xem danh mục"},
    "category.update": {"group": PermissionGroup.CATEGORY, "label": "Cập nhật danh mục"},
    "category.delete": {"group": PermissionGroup.CATEGORY, "label": "Xóa danh mục"},
    "category.list":   {"group": PermissionGroup.CATEGORY, "label": "Danh sách danh mục"},
    
    # --- Data Source ---
    "data_source.create": {"group": PermissionGroup.DATA_SOURCE, "label": "Tạo nguồn dữ liệu"},
    "data_source.read":   {"group": PermissionGroup.DATA_SOURCE, "label": "Xem nguồn dữ liệu"},
    "data_source.update": {"group": PermissionGroup.DATA_SOURCE, "label": "Cập nhật nguồn dữ liệu"},
    "data_source.delete": {"group": PermissionGroup.DATA_SOURCE, "label": "Xóa nguồn dữ liệu"},
    "data_source.list":   {"group": PermissionGroup.DATA_SOURCE, "label": "Danh sách nguồn dữ liệu"},

    # --- Crawl History ---
    # "crawl_history.read":   {"group": PermissionGroup.CRAWL_HISTORY, "label": "Xem lịch sử cào"},
    # "crawl_history.list":   {"group": PermissionGroup.CRAWL_HISTORY, "label": "Danh sách lịch sử cào"},
    # "crawl_history.delete": {"group": PermissionGroup.CRAWL_HISTORY, "label": "Xóa lịch sử cào"},

    # --- Crawler Config ---
    "crawler_config.create": {"group": PermissionGroup.CRAWLER_CONFIG, "label": "Tạo cấu hình cào"},
    "crawler_config.read":   {"group": PermissionGroup.CRAWLER_CONFIG, "label": "Xem cấu hình cào"},
    "crawler_config.update": {"group": PermissionGroup.CRAWLER_CONFIG, "label": "Cập nhật cấu hình cào"},
    "crawler_config.delete": {"group": PermissionGroup.CRAWLER_CONFIG, "label": "Xóa cấu hình cào"},
    "crawler_config.list":   {"group": PermissionGroup.CRAWLER_CONFIG, "label": "Danh sách cấu hình cào"},

    # --- CV Profile ---
    "cv_profile.read":   {"group": PermissionGroup.CV_PROFILE, "label": "Xem hồ sơ CV"},
    "cv_profile.update": {"group": PermissionGroup.CV_PROFILE, "label": "Cập nhật hồ sơ CV"},
    "cv_profile.delete": {"group": PermissionGroup.CV_PROFILE, "label": "Xóa hồ sơ CV"},
    "cv_profile.list":   {"group": PermissionGroup.CV_PROFILE, "label": "Danh sách hồ sơ CV"},

    # --- Job Favorite ---
    # "job_favorite.read":   {"group": PermissionGroup.JOB_FAVORITE, "label": "Xem việc làm yêu thích"},
    # "job_favorite.list":   {"group": PermissionGroup.JOB_FAVORITE, "label": "Danh sách việc làm yêu thích"},
}

def require_permission(perms: Union[List[str], str]):
    if isinstance(perms, str):
        perms = [perms]

    # Validate at startup
    for perm in perms:
        if perm not in PERMISSION_DEFINITIONS:
            # print(f"WARNING: Permission '{perm}' is not defined in PERMISSION_DEFINITIONS.")
            pass

    def decorator(func):
        async def wrapper(*args, user_perms: List[str] = None, **kwargs):
            if user_perms is None:
                raise PermissionError("Missing user permissions context")

            # --- FULL ACCESS CHECK ---
            # Nếu user có "*" thì cho full quyền
            if "*" in user_perms:
                return await func(*args, user_perms=user_perms, **kwargs)

            # --- NORMAL PERMISSION CHECK ---
            for perm in perms:
                if (
                    perm in user_perms or
                    f"{perm.split('.')[0]}.*" in user_perms
                ):
                    return await func(*args, user_perms=user_perms, **kwargs)

            raise PermissionError(f"Missing one of required permissions: {perms}")

        return wrapper
    return decorator

def get_all_permissions() -> List[str]:
    # Returns the list of permission keys
    return sorted(PERMISSION_DEFINITIONS.keys())

def get_all_permissions_grouped() -> dict:
    grouped = {}
    for perm_key, meta in sorted(PERMISSION_DEFINITIONS.items()):
        group_name = meta["group"].value
        if group_name not in grouped:
            grouped[group_name] = []
        grouped[group_name].append({
            "perm": perm_key,
            "label": meta["label"],
        })
    return grouped
