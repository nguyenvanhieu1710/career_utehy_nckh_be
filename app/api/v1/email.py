
from fastapi import FastAPI, BackgroundTasks, APIRouter, Depends
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from app.schemas.email import EmailSchema
from app.utils import auth
from app.core.email import settings
from datetime import datetime, timedelta
from app.services import user_service, otp_service
from app.core.database import Base, engine, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async with SessionLocal() as session:
        yield session

email_conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
)
router = APIRouter()

@router.post("/verify-mail/{token}")
async def verify(token: str, db: AsyncSession=Depends(get_db)):
    payload = auth.verify_token(token)
    if not payload:
        return {"status": "failed", "error": "Unauthorize token!"}
    exist_user = await user_service.get_user_by_email(email=payload["email"], db=db)
    if exist_user:
        return {"status": "failed", "error": "Email has exist!"}
    new_user_encode = await user_service.create(email=payload["email"], 
                                          username=user_service.get_email_username(email=payload["email"]), 
                                          password=user_service.generate_random_password(12), db=db)
    
    return {"status": "success", "message": "Verify successffully!", 'data': new_user_encode}

@router.post("/verify-mail-forgot-password/{token}")
async def verify(token: str, db: AsyncSession=Depends(get_db)):
    payload = auth.verify_token(token)
    if not payload:
        return {"status": "failed", "error": "Unauthorize token!"}
    new_user_encode = await user_service.verify_success(email=payload["email"], db=db)
    
    return {"status": "success", "message": "Verify successffully!", 'data': new_user_encode}

@router.post("/send-verify-mail/{email}")
async def send_email(email: str, background_tasks: BackgroundTasks, db: AsyncSession=Depends(get_db)):
    exist_user = await user_service.user_is_exist(email=email, db=db)
    if exist_user:
        return {"status": "failed", "error": "Email has exist!"}
    message = MessageSchema(
        subject="Alex - Verify your email",
        recipients=[email],
        body = f"""
        <div style="width: 100%; min-height: 500px; display: flex; justify-content: center; align-items: center; background-color: #f8f9fa; font-family: Arial, sans-serif;">
            <div style="margin: 0 auto; width: 100%; max-width: 480px; padding: 40px 30px; border-radius: 12px; 
                        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); justify-content: center; 
                        align-items: center; color: #ffffff; text-align: center; border: 1px solid #333; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                
                <!-- Logo/Brand -->
                <div style="margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 48px; font-weight: bold; color: #CB2F30; letter-spacing: 2px;">ALEX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #cccccc; font-weight: 300;">TOOLS PLATFORM</p>
                </div>
                
                <!-- Separator -->
                <div style="height: 2px; background: linear-gradient(90deg, transparent 0%, #CB2F30 50%, transparent 100%); margin: 25px 0;"></div>
                
                <!-- Content -->
                <div style="margin-bottom: 35px;">
                    <h3 style="margin: 0 0 15px 0; font-size: 22px; font-weight: 600; color: #ffffff;">Email Verification Required</h3>
                    <p style="margin: 0; font-size: 15px; line-height: 1.5; color: #e0e0e0;">
                        Please verify your email address to continue using Alex Tools platform and access all features.
                    </p>
                </div>
                
                <!-- CTA Button -->
                <a href="http://localhost:3000/auth/verify-email/{auth.create_access_token(data={"name":"verify", 'email': email}, expires_delta=timedelta(minutes=15))}" 
                style="display: inline-block; text-decoration: none; text-align: center; font-weight: 600;
                        width: 180px; height: 48px; line-height: 48px; font-size: 15px; letter-spacing: 0.5px;
                        color: #ffffff; background: linear-gradient(135deg, #CB2F30 0%, #A02525 100%); 
                        border-radius: 6px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(203, 47, 48, 0.3);">
                    Verify Email Address
                </a>
                
                <!-- Footer Note -->
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #444;">
                    <p style="margin: 0; font-size: 12px; color: #999;">
                        This verification link expires in 15 minutes<br>
                        If you didn't request this, please ignore this email
                    </p>
                </div>
            </div>
        </div>
        """,

        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    
@router.post("/send-otp-email")
async def send_otp(current_password: str, db: AsyncSession=Depends(get_db), user: dict = Depends(auth.decode_token_user)):
    email = user.get("email")
    otp = await otp_service.create_otp(email=email)
    correct_password = await user_service.verify_password_user(email=email, password=current_password, db=db)
    if not correct_password:
        return {"status": "failed", "error": "Incorrect current password"}
    message = MessageSchema(
        subject="Alex - Verify your email",
        recipients=[email],
        body = f"""
       <div style="width: 100%; min-height: 500px; display: flex; justify-content: center; align-items: center; background-color: #f8f9fa; font-family: Arial, sans-serif;">
            <div style="margin: 0 auto; width: 100%; max-width: 480px; padding: 40px 30px; border-radius: 12px; 
                        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); justify-content: center; 
                        align-items: center; color: #ffffff; text-align: center; border: 1px solid #333; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                
                <!-- Logo/Brand -->
                <div style="margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 48px; font-weight: bold; color: #CB2F30; letter-spacing: 2px;">ALEX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #cccccc; font-weight: 300;">TOOLS PLATFORM</p>
                </div>
                
                <!-- Separator -->
                <div style="height: 2px; background: linear-gradient(90deg, transparent 0%, #CB2F30 50%, transparent 100%); margin: 25px 0;"></div>
                
                <!-- Content -->
                <div style="margin-bottom: 35px;">
                    <h3 style="margin: 0 0 15px 0; font-size: 22px; font-weight: 600; color: #ffffff;">Your Verification Code</h3>
                    <p style="margin: 0 0 20px 0; font-size: 15px; line-height: 1.5; color: #e0e0e0;">
                        Use the following OTP code to complete your verification process:
                    </p>
                    
                    <!-- OTP Code Display -->
                    <div style="background: rgba(203, 47, 48, 0.1); border: 2px solid #CB2F30; border-radius: 8px; 
                                padding: 20px; margin: 25px 0;">
                        <p style="margin: 0; font-size: 13px; color: #cccccc; font-weight: 500; letter-spacing: 1px;">
                            YOUR VERIFICATION CODE
                        </p>
                        <div style="font-size: 32px; font-weight: bold; color: #CB2F30; letter-spacing: 8px; 
                                    margin: 10px 0; font-family: 'Courier New', monospace;">
                            {otp}
                        </div>
                        <p style="margin: 0; font-size: 12px; color: #999;">
                            Valid for 1 minutes
                        </p>
                    </div>
                    
                    <p style="margin: 0; font-size: 14px; color: #e0e0e0;">
                        Enter this code in the verification page to proceed.
                    </p>
                </div>
            
                
                <!-- Security Warning -->
                <div style="margin-top: 30px; padding: 15px; background: rgba(255, 255, 255, 0.05); border-radius: 6px;">
                    <p style="margin: 0; font-size: 12px; color: #ff6b6b;">
                        ⚠️ <strong>Security Alert:</strong> Never share this code with anyone. Alex Tools will never ask for your verification code.
                    </p>
                </div>
                
                <!-- Footer Note -->
                <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #444;">
                    <p style="margin: 0; font-size: 12px; color: #999;">
                        If you didn't request this verification, please ignore this email<br>
                        or contact our support team immediately.
                    </p>
                </div>
            </div>
        </div>
        """,

        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.post("/send-email-forgot-password/{email}")
async def send_email(email: str, background_tasks: BackgroundTasks, db: AsyncSession=Depends(get_db)):
    exist_user = await user_service.user_is_exist(email=email, db=db)
    if not exist_user:
        return {"status": "failed", "error": "Email not exist!"}
    message = MessageSchema(
        subject="Alex - Verify your email",
        recipients=[email],
        body = f"""
        <div style="width: 100%; min-height: 500px; display: flex; justify-content: center; align-items: center; background-color: #f8f9fa; font-family: Arial, sans-serif;">
            <div style="margin: 0 auto; width: 100%; max-width: 480px; padding: 40px 30px; border-radius: 12px; 
                        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); justify-content: center; 
                        align-items: center; color: #ffffff; text-align: center; border: 1px solid #333; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                
                <!-- Logo/Brand -->
                <div style="margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 48px; font-weight: bold; color: #CB2F30; letter-spacing: 2px;">ALEX</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #cccccc; font-weight: 300;">TOOLS PLATFORM</p>
                </div>
                
                <!-- Separator -->
                <div style="height: 2px; background: linear-gradient(90deg, transparent 0%, #CB2F30 50%, transparent 100%); margin: 25px 0;"></div>
                
                <!-- Content -->
                <div style="margin-bottom: 35px;">
                    <h3 style="margin: 0 0 15px 0; font-size: 22px; font-weight: 600; color: #ffffff;">Email Verification Required</h3>
                    <p style="margin: 0; font-size: 15px; line-height: 1.5; color: #e0e0e0;">
                        Please verify your email address to continue using Alex Tools platform and access all features.
                    </p>
                </div>
                
                <!-- CTA Button -->
                <a href="http://localhost:3000/auth/verify-email-forgot-password/{auth.create_access_token(data={"name":"verify", 'email': email}, expires_delta=timedelta(minutes=15))}" 
                style="display: inline-block; text-decoration: none; text-align: center; font-weight: 600;
                        width: 180px; height: 48px; line-height: 48px; font-size: 15px; letter-spacing: 0.5px;
                        color: #ffffff; background: linear-gradient(135deg, #CB2F30 0%, #A02525 100%); 
                        border-radius: 6px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(203, 47, 48, 0.3);">
                    Verify Email Address
                </a>
                
                <!-- Footer Note -->
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #444;">
                    <p style="margin: 0; font-size: 12px; color: #999;">
                        This verification link expires in 15 minutes<br>
                        If you didn't request this, please ignore this email
                    </p>
                </div>
            </div>
        </div>
        """,

        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    