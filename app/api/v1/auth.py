from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, Form, status
from sqlalchemy.future import select
from app.services import user_service, otp_service
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.models.user import UserSignin, UserLogin, UserUpdate, AddRole, AddPerm, UserCreateByAdmin, UpdateUserRoles, Users
from sqlalchemy.dialects.postgresql import UUID
import uuid
import json
from app.utils import auth
from app.core.perms import require_permission

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session



@router.post("/signup")
async def user_signin(data: UserSignin, db: AsyncSession = Depends(get_db)):
    result = await user_service.create(email=data.email,
                                       username=data.username,
                                       password=data.password,
                                       db=db)
    if not result:
        raise HTTPException(status_code=400, detail="Incorrect email or password!")
    return result


@router.post("/login")
async def user_login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await user_service.login(email=data.email,
                                       password=data.password,
                                       db=db)
    return result


@router.get("/verify")
async def user_login(db: AsyncSession = Depends(get_db), user_id: str = Depends(auth.verify_token_user)):
    result = await user_service.get_user_by_user_id_decode_token(id=user_id, db=db)
    return result

@router.get("/get-by-email/{email}")
async def user_login(email: str, db: AsyncSession = Depends(get_db)):
    result = await user_service.get_user_by_email(email=email, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.patch("/update")
async def user_login(data: UserUpdate, 
                     db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(auth.verify_token_user)):
    try:
        result = await user_service.update_user(user_id=user_id, data=data, db=db)
        return {'status':'success', 'data': result}
    except HTTPException as ex:
        return ex
    

@router.patch("/update-password")
async def user_update(token: str, data: UserUpdate, 
                     db: AsyncSession = Depends(get_db)):
    try:
        user_payload = auth.verify_token(token=token)
        print(user_payload)
        result = await user_service.update_user_by_email(email=user_payload["email"], data=data, db=db)
        return {'status':'success','detail': 'Đổi mật khẩu thành công', 'data': result}
    except HTTPException as ex:
        return ex


@router.patch("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Change password for logged-in user
    Requires current password verification
    """
    try:
        result = await user_service.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
            db=db
        )
        return {
            'status': 'success',
            'detail': 'Đổi mật khẩu thành công',
            'data': result
        }
    except HTTPException as ex:
        raise ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/add-role")
async def user_add_role_endpoint(data: AddRole, 
                     db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(auth.verify_token_user)):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.user_add_role(user_perms=perms, data=data, db=db)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException as ex:
        raise ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/get-roles")
async def user_update(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await user_service.get_user_roles(user_id=user_id, db=db)
        return {'status':'success', 'data': result}
    except HTTPException as ex:
        return ex

@router.post("/verify-otp")
async def check_otp(otp: str, new_password: str, user: dict = Depends(auth.decode_token_user), db:AsyncSession = Depends(get_db)):
    email = user.get("email")
    user_id = user.get("user_id")
    valid = await otp_service.verify_otp(email, otp)
    if not valid:
        raise HTTPException(status_code=400, detail="OTP invalid or expired!")
    new_data = UserUpdate()
    new_data.password = new_password
    new_user = await user_service.update_user(user_id=user_id, data=new_data, db=db)
    return {"status":"success","message": "Verify OTP successfully!", "data":new_user}


@router.get("/me")
async def get_current_user(
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """
    Get current user's profile without permission check
    Users can always view their own profile
    """
    try:
        result = await db.execute(select(Users).where(Users.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"status": "success", "data": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/me")
async def update_current_user(
        data: UserUpdate,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    """
    Update current user's profile without permission check
    Users can always update their own profile
    """
    try:
        result = await db.execute(select(Users).where(Users.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
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

        await db.commit()
        await db.refresh(user)
        return {"status": "success", "data": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/get-users")
async def get_users(
        data: get_schema.GetSchema, 
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    try:
        print("=" * 60)
        print("📥 GET USERS REQUEST")
        print(f"User ID: {user_id}")
        print(f"Filters: {data}")
        
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        result = await user_service.get_all_users(user_perms=perms, filters=data, db=db)
        print(f"✅ Success: Found {result.get('total', 0)} users")
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


@router.get("/get-user/{target_user_id}")
async def get_user_detail(
        target_user_id: str,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.get_user_by_id(user_perms=perms, user_id=target_user_id, db=db)
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


@router.put("/update-user/{target_user_id}")
async def update_user_admin(
        target_user_id: str,
        data: UserUpdate,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.update_user_by_id(user_perms=perms, user_id=target_user_id, data=data, db=db)
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


@router.delete("/delete-user/{target_user_id}")
async def delete_user_admin(
        target_user_id: str,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.delete_user(user_perms=perms, user_id=target_user_id, db=db)
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


@router.post("/create-user")
async def create_user_admin(
        data: UserCreateByAdmin,
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(auth.verify_token_user)
    ):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.create_user_by_admin(user_perms=perms, data=data, db=db)
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


@router.post("/upload-avatar/{target_user_id}")
async def upload_user_avatar(
    target_user_id: str,
    file: UploadFile = Form(..., description="Avatar image file"),
    optimize: bool = Form(True, description="Whether to optimize the uploaded image"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Upload avatar for a specific user
    
    - **target_user_id**: ID of the user to update
    - **file**: Avatar image file (jpg, jpeg, png, gif, webp)
    - **optimize**: Whether to optimize image (resize + compress)
    
    Returns uploaded avatar information and updates user
    """
    try:
        print("=" * 60)
        print("📤 USER AVATAR UPLOAD REQUEST")
        print(f"Admin User ID: {user_id}")
        print(f"Target User ID: {target_user_id}")
        print(f"File name: {file.filename}")
        print(f"Content type: {file.content_type}")
        
        # Check user permissions
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"User permissions: {perms}")
        
        # Check if target user exists
        target_user = await user_service.get_user_by_id(user_perms=perms, user_id=target_user_id, db=db)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Import upload service
        from app.services.upload_service import upload_service
        
        # Upload avatar file
        upload_result = await upload_service.upload_single_file(
            file=file,
            file_type="users",
            optimize=optimize
        )
        
        print(f"✅ Avatar uploaded: {upload_result['file_url']}")
        
        # Update user with new avatar URL
        update_data = UserUpdate(avatar_url=upload_result['file_url'])
        updated_user = await user_service.update_user_by_id(
            user_perms=perms,
            user_id=target_user_id,
            data=update_data,
            db=db
        )
        
        print(f"✅ User updated with new avatar")
        print("=" * 60)
        
        return {
            "status": "success",
            "message": "User avatar uploaded successfully",
            "avatar_info": upload_result,
            "user": updated_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Avatar Upload Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar upload failed: {str(e)}"
        )


@router.delete("/remove-avatar/{target_user_id}")
async def remove_user_avatar(
    target_user_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Remove avatar from a specific user
    
    - **target_user_id**: ID of the user to update
    
    Returns success message and updates user
    """
    try:
        print(f"🗑️ REMOVE USER AVATAR: {target_user_id} by admin {user_id}")
        
        # Check user permissions
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        
        # Check if target user exists
        target_user = await user_service.get_user_by_id(user_perms=perms, user_id=target_user_id, db=db)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user to remove avatar (set to None/empty)
        update_data = UserUpdate(avatar_url="")
        updated_user = await user_service.update_user_by_id(
            user_perms=perms,
            user_id=target_user_id,
            data=update_data,
            db=db
        )
        
        print(f"✅ User avatar removed successfully")
        
        return {
            "status": "success",
            "message": "User avatar removed successfully",
            "user": updated_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Remove Avatar Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove avatar: {str(e)}"
        )


@router.get("/get-user-roles-permissions/{target_user_id}")
async def get_user_roles_permissions(
    target_user_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get user with their roles and permissions
    """
    try:
        print(f"📥 GET /get-user-roles-permissions/{target_user_id} from user {user_id}")
        
        # Validate target_user_id format
        try:
            import uuid
            uuid.UUID(target_user_id)
        except ValueError:
            print(f"❌ Invalid UUID format: {target_user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID format: {target_user_id}"
            )
        
        # Check permissions
        print(f"🔍 Checking permissions for user {user_id}...")
        try:
            perms = await user_service.get_user_permissions(user_id=user_id, db=db)
            print(f"📊 User {user_id} permissions: {perms}")
        except Exception as perm_error:
            print(f"❌ Error getting permissions for user {user_id}: {str(perm_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error checking permissions: {str(perm_error)}"
            )
        
        if "user.read" not in perms and "*" not in perms:
            print(f"❌ Permission denied for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: user.read required"
            )
        
        print(f"✅ Permission check passed for user {user_id}")
        
        # Get user roles and permissions
        try:
            result = await user_service.get_user_with_roles_permissions(user_id=target_user_id, db=db)
            print(f"✅ Get user roles/permissions API success for target user {target_user_id}")
            return {"status": "success", "data": result}
        except Exception as get_error:
            print(f"❌ Error getting user roles/permissions for {target_user_id}: {str(get_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting user data: {str(get_error)}"
            )
            
    except HTTPException:
        raise
    except PermissionError as e:
        print(f"❌ Permission error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Unexpected error in get-user-roles-permissions endpoint: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/update-user-roles/{target_user_id}")
async def update_user_roles(
    target_user_id: str,
    data: UpdateUserRoles,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Update user roles and permissions
    """
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.update_user_roles_permissions(
            user_perms=perms, 
            user_id=target_user_id, 
            data=data, 
            db=db
        )
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


@router.get("/available-roles")
async def get_available_roles(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all available roles
    """
    try:
        print("🚀 AVAILABLE-ROLES ENDPOINT CALLED - NEW CODE LOADED!")
        print(f"📥 GET /available-roles request from user {user_id}")
        
        # Check permissions
        print(f"🔍 Checking permissions for user {user_id}...")
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        print(f"📊 User {user_id} permissions: {perms}")
        
        if "user.read" not in perms and "*" not in perms:
            print(f"❌ Permission denied for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: user.read required"
            )
        
        print(f"✅ Permission check passed for user {user_id}")
        result = await user_service.get_available_roles(db=db)
        print(f"✅ Available roles API success: {len(result)} roles")
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in available-roles endpoint: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error in available-roles: {str(e)}"
        )


@router.get("/available-permissions")
async def get_available_permissions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(auth.verify_token_user)
):
    """
    Get all available permissions
    """
    try:
        # Check permissions
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        if "user.read" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # Import permissions from core
        from app.core import perms as core_perms
        all_permissions = core_perms.get_all_permissions()
        
        return {"status": "success", "data": all_permissions}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )