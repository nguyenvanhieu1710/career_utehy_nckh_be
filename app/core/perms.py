PERMISSION_REGISTRY: set[str] = set()

def require_permission(perms: list[str] | str):
    if isinstance(perms, str):
        perms = [perms]
    PERMISSION_REGISTRY.update(perms)

    def decorator(func):
        async def wrapper(*args, user_perms: list[str] = None, **kwargs):
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
                    perm.split(".")[0] + ".*" in user_perms
                ):
                    return await func(*args, user_perms=user_perms, **kwargs)

            raise PermissionError(f"Missing one of required permissions: {perms}")

        return wrapper
    return decorator


def get_all_permissions() -> list[str]:
    return sorted(PERMISSION_REGISTRY)
