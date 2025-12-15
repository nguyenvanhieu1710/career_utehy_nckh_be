from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from app.models.user import Users, UserSignin, UserUpdate, UserRole, UserPerm, AddPerm, AddRole
from app.models.perm_groups import PermGroups, GroupPermission
from app.models import perm_groups
from app.schemas import get_schema
from passlib.context import CryptContext
from app.utils import auth
from sqlalchemy.exc import IntegrityError
import string
import secrets
import math
import os
from app.core.perms import require_permission
from app.services.upload_service import upload_service

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def create(
        email: str,
        username: str, 
        password: str, 
        fullname: str,
        db: AsyncSession):
    """
    """
    try:
        new_user = Users(email=email, 
                            username=username, 
                            password_hash=hash_password(password=password),
                            fullname=fullname,
                            action_status="active"
                            )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        payload = {
            'user_id': str(new_user.id),
            'email': str(new_user.email)
        }
        token = auth.create_access_token(data=payload, expires_delta=timedelta(days=15))

        return {"access_token": token, 
                "token_type": "bearer",
                "user_id": new_user.id,
                "user_name": new_user.username,
                "fullname": new_user.fullname,
                "email": new_user.email}
    except IntegrityError as err:
        await db.rollback()
        return {"error": "Email already used"}
    
async def login(
        email: str,
        password: str, 
        db: AsyncSession):
    """
    """
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Incorrect email or password")
    if not verify_password(plain_password=password, hashed_password=user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    payload = {
        'user_id': str(user.id),
        'email': str(user.email)
    }
    token = auth.create_access_token(data=payload, expires_delta=timedelta(days=15))

    return {"access_token": token, 
            "token_type": "bearer",
            "user_id": user.id,
            "user_name": user.username,
            "fullname": user.fullname,
            "email": user.email}

async def get_user_by_user_id_decode_token(
        id: str,
        db: AsyncSession):
    """
    """
    result = await db.execute(select(Users).where(Users.id == id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")

    payload = {
        'user_id': str(user.id),
        'email': str(user.email)
    }
    token = auth.create_access_token(data=payload, expires_delta=timedelta(days=15))

    return {"access_token": token, 
            "token_type": "bearer",
            "user_id": user.id,
            "user_name": user.username,
            "fullname": user.fullname,
            "email": user.email}

async def verify_success(
        email: str,
        db: AsyncSession):
    """
    """
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    print(user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    payload = {
        'user_id': str(user.id),
        'email': str(user.email)
    }
    token = auth.create_access_token(data=payload, expires_delta=timedelta(days=15))

    return {"access_token": token, 
            "token_type": "bearer",
            "user_id": user.id,
            "user_name": user.username,
            "email": user.email}

async def get_user_by_email(email:str, db: AsyncSession) -> UserSignin:
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    del user.password_hash
    del user.id
    return user

async def user_is_exist(email:str, db: AsyncSession) -> UserSignin:
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        return False
    return True

async def verify_password_user(email:str, password: str, db: AsyncSession) -> UserSignin:
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(plain_password=password, hashed_password=user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    return True

@require_permission(['user.update'])
async def user_add_role(user_perms: list[str], data: AddRole, db: AsyncSession):
    try:
        new_item = UserRole(
            user_id=data.user_id,
            group_id=data.group_id
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return {"status": "success", "data": new_item}
    except Exception as ex:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(ex)}"
        )

async def update_user_by_email(email: str, data: UserUpdate, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if data.username:
        user.username = data.username
    if data.password:
        user.password_hash = hash_password(data.password)

    await db.commit()
    await db.refresh(user)
    del user.password_hash
    return user    


async def update_user(user_id:str, data: UserUpdate, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if data.username:
        user.username = data.username
    if data.password:
        user.password_hash = hash_password(data.password)

    await db.commit()
    await db.refresh(user)
    del user.password_hash
    return user


async def change_password(user_id: str, current_password: str, new_password: str, db: AsyncSession):
    """
    Change password for logged-in user with current password verification
    """
    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(plain_password=current_password, hashed_password=user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng"
        )
    
    # Update to new password
    user.password_hash = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    
    # Remove sensitive data before returning
    del user.password_hash
    return user    

def get_email_username(email: str) -> str | None:
    if not isinstance(email, str) or "@" not in email:
        return None
    return email.split("@")[0]

def generate_random_password(length: int = 12) -> str:
    if length < 4:
        raise ValueError("Password length should be at least 4")
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(chars) for _ in range(length))
    return password

async def get_user_roles(user_id: str, db: AsyncSession) -> list[str]:
    stmt = (
        select(PermGroups.id)
        .join(UserRole, UserRole.group_id == PermGroups.id)
        .where(UserRole.user_id == user_id)
    )
    result = await db.execute(stmt)
    group_ids = [str(group_id) for group_id in result.scalars().all()]
    return group_ids



async def get_user_permissions(user_id: str, db: AsyncSession) -> list[str]:
    stmt_user_perms = select(UserPerm.perm).where(UserPerm.user_id == user_id)
    result_user_perms = await db.execute(stmt_user_perms)
    direct_perms = set(result_user_perms.scalars().all())

    stmt_group_perms = (
        select(GroupPermission.perm)
        .join(PermGroups, GroupPermission.group_id == PermGroups.id)
        .join(UserRole, UserRole.group_id == PermGroups.id)
        .where(UserRole.user_id == user_id)
    )
    result_group_perms = await db.execute(stmt_group_perms)
    group_perms = set(result_group_perms.scalars().all())

    all_perms = list(direct_perms.union(group_perms))
    return all_perms


@require_permission(["user.list"])
async def get_all_users(user_perms: list[str], filters: get_schema.GetSchema, db: AsyncSession):
    base_stmt = select(Users)
    
    # Filter out deleted users (soft delete) - allow NULL values for backward compatibility
    base_stmt = base_stmt.where((Users.action_status != "deleted") | (Users.action_status.is_(None)))

    if filters.id:
        base_stmt = base_stmt.where(Users.id == filters.id)

    if filters.searchKeyword:
        keyword = f"%{filters.searchKeyword}%"
        base_stmt = base_stmt.where(
            (Users.username.ilike(keyword)) |
            (Users.email.ilike(keyword))
        )

    page = filters.page if filters.page and filters.page > 0 else 1
    row = min(filters.row if filters.row and filters.row > 0 else 10, 100)
    offset = (page - 1) * row
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
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


@require_permission(["user.update"])
async def update_user_by_id(user_perms: list[str], user_id: str, data: UserUpdate, db: AsyncSession):
    result = await db.execute(select(Users).where(
        (Users.id == user_id) & 
        ((Users.action_status != "deleted") | (Users.action_status.is_(None)))
    ))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Handle avatar cleanup if avatar_url is being changed
    old_avatar_url = user.avatar_url
    cleanup_old_avatar = False
    
    if data.avatar_url is not None and data.avatar_url != old_avatar_url:
        cleanup_old_avatar = True
        print(f"🔄 Avatar change detected: '{old_avatar_url}' -> '{data.avatar_url}'")
    
    # Update basic fields
    if data.username:
        user.username = data.username
    if data.email:
        user.email = data.email
    if data.password:
        user.password_hash = hash_password(data.password)
    
    # Update profile fields
    if data.fullname:
        user.fullname = data.fullname
    if data.phone:
        user.phone = data.phone
    if data.address:
        user.address = data.address
    if data.birthday:
        # Convert string to date object
        try:
            from datetime import datetime
            user.birthday = datetime.strptime(data.birthday, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Expected YYYY-MM-DD"
            )
    if data.gender:
        user.gender = data.gender
    if data.avatar_url is not None:  # Allow empty string to clear avatar_url
        user.avatar_url = data.avatar_url

    await db.commit()
    await db.refresh(user)
    
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
    
    return user


@require_permission(["user.delete"])
async def delete_user(user_perms: list[str], user_id: str, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Store avatar URL for cleanup
    avatar_url = user.avatar_url
    
    # Soft delete - change action_status to "deleted"
    user.action_status = "deleted"
    await db.commit()
    await db.refresh(user)
    
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
                        print(f"✅ Avatar deleted with user: {full_path}")
                    else:
                        print(f"⚠️ Failed to delete avatar: {full_path}")
                else:
                    print(f"⚠️ Avatar file not found: {full_path}")
        except Exception as e:
            print(f"⚠️ Error cleaning up avatar on delete: {str(e)}")
            # Don't fail the delete if cleanup fails
    
    return {"status": "success", "message": "User deleted successfully"}


@require_permission(["user.read"])
async def get_user_by_id(user_perms: list[str], user_id: str, db: AsyncSession):
    result = await db.execute(select(Users).where(
        (Users.id == user_id) & 
        ((Users.action_status != "deleted") | (Users.action_status.is_(None)))
    ))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@require_permission(["user.create"])
async def create_user_by_admin(user_perms: list[str], data, db: AsyncSession):
    """
    Admin creates a new user with permission check
    """
    try:
        # Check if email already exists
        result = await db.execute(select(Users).where(Users.email == data.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Create new user
        new_user = Users(
            email=data.email, 
            username=data.username, 
            password_hash=hash_password(password=data.password),
            fullname=data.fullname,
            action_status="active"
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Remove password hash from response
        del new_user.password_hash
        
        return {
            "status": "success",
            "message": "User created successfully",
            "data": new_user
        }
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already used"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
