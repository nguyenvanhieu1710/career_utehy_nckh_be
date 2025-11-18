from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, UploadFile, Response, Query, Depends, HTTPException, Form, status
from app.services import user_service, otp_service
from app.schemas import get_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.models.user import UserSignin, UserLogin, UserUpdate, AddRole, AddPerm
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

@router.post("/add-role")
async def user_update(data: AddRole, 
                     db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(auth.verify_token_user)):
    try:
        perms = await user_service.get_user_permissions(user_id=user_id, db=db)
        result = await user_service.user_add_role(user_perms=perms, data=data, db=db)
        return {'status':'success', 'data': result}
    except HTTPException as ex:
        return ex

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


@router.post("/get")
async def get_users(
        data: get_schema.GetSchema, 
        db: AsyncSession = Depends(get_db),
        perms: list = Depends(auth.get_current_user_permissions)
    ):
    try:
        result = await user_service.get_all_users(user_perms=perms, filters=data, db=db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )