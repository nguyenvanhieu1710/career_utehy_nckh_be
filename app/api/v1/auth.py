from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, Form, status
from app.services import user_service, otp_service
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.models.user import UserSignin, UserLogin, UserUpdate, AddRole, AddPerm, UserCreateByAdmin
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