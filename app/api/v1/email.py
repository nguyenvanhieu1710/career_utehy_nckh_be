from fastapi import FastAPI, BackgroundTasks, APIRouter, Depends
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.utils import auth
from app.core.email import settings
from datetime import datetime, timedelta
from app.services import user_service, otp_service
from app.core.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async with SessionLocal() as session:
        yield session

# ---------- EMAIL CONFIG ----------
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


# ---------- TEMPLATE FUNCTION ----------
def generate_email_html(type_: str, token_or_otp: str = None):
    main_color = "#2E7D32"  # xanh lá đậm
    accent_color = "#43A047"
    text_color = "#333"
    bg_color = "#f5fdf6"
    border_color = "#c8e6c9"

    if type_ == "verify":
        action_text = "Verify Email Address"
        action_url = f"http://localhost:3000/auth/verify-email/{token_or_otp}"
        body = f"""
        <p style="font-size:16px;color:{text_color};">Please verify your email address to continue using our platform.</p>
        <a href="{action_url}" 
            style="display:inline-block;text-decoration:none;background:{main_color};color:white;
                   padding:12px 28px;border-radius:6px;font-weight:bold;margin-top:16px;">
            {action_text}
        </a>
        <p style="font-size:12px;color:#555;margin-top:20px;">This link will expire in 15 minutes.</p>
        """
    elif type_ == "forgot_password":
        action_text = "Reset Password"
        action_url = f"http://localhost:3000/auth/verify-email-forgot-password/{token_or_otp}"
        body = f"""
        <p style="font-size:16px;color:{text_color};">Click the button below to reset your password:</p>
        <a href="{action_url}" 
            style="display:inline-block;text-decoration:none;background:{main_color};color:white;
                   padding:12px 28px;border-radius:6px;font-weight:bold;margin-top:16px;">
            {action_text}
        </a>
        <p style="font-size:12px;color:#555;margin-top:20px;">This link will expire in 15 minutes.</p>
        """
    elif type_ == "otp":
        body = f"""
        <p style="font-size:16px;color:{text_color};">Use the following verification code:</p>
        <div style="margin:16px auto;padding:20px;border:2px dashed {main_color};
                    width:fit-content;border-radius:8px;">
            <span style="font-size:32px;font-weight:bold;color:{main_color};letter-spacing:6px;">{token_or_otp}</span>
        </div>
        <p style="font-size:14px;color:#555;">Valid for 1 minute. Do not share this code with anyone.</p>
        """
    else:
        body = "<p>Unknown email type</p>"

    return f"""
    <div style="width:100%;background:{bg_color};padding:40px 0;font-family:Arial, sans-serif;">
        <div style="margin:0 auto;max-width:500px;background:white;border:1px solid {border_color};
                    border-radius:10px;padding:30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.05);">
            <h1 style="color:{main_color};margin-bottom:10px;">CAREER</h1>
            <p style="margin-top:0;color:{accent_color};font-size:14px;">Tìm kiếm việc làm phù hợp</p>
            <hr style="border:none;height:1px;background:{border_color};margin:20px 0;">
            {body}
            <hr style="border:none;height:1px;background:{border_color};margin:20px 0;">
            <p style="font-size:12px;color:#777;">If you didn’t request this email, please ignore it.</p>
        </div>
    </div>
    """


# ---------- ROUTES ----------

@router.post("/verify-mail/{token}")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    payload = auth.verify_token(token)
    if not payload:
        return {"status": "failed", "error": "Unauthorize token!"}
    exist_user = await user_service.get_user_by_email(email=payload["email"], db=db)
    if exist_user:
        return {"status": "failed", "error": "Email has exist!"}
    new_user_encode = await user_service.create(
        email=payload["email"],
        username=user_service.get_email_username(email=payload["email"]),
        password=user_service.generate_random_password(12),
        db=db
    )
    return {"status": "success", "message": "Verify successffully!", "data": new_user_encode}


@router.post("/verify-mail-forgot-password/{token}")
async def verify_forgot(token: str, db: AsyncSession = Depends(get_db)):
    payload = auth.verify_token(token)
    if not payload:
        return {"status": "failed", "error": "Unauthorize token!"}
    new_user_encode = await user_service.verify_success(email=payload["email"], db=db)
    return {"status": "success", "message": "Verify successffully!", "data": new_user_encode}


@router.post("/send-verify-mail/{email}")
async def send_verify_email(email: str, db: AsyncSession = Depends(get_db)):
    exist_user = await user_service.user_is_exist(email=email, db=db)
    if exist_user:
        return {"status": "failed", "error": "Email has exist!"}

    token = auth.create_access_token(data={"name": "verify", "email": email}, expires_delta=timedelta(minutes=15))
    html = generate_email_html("verify", token)

    message = MessageSchema(
        subject="CAREER - Verify your email",
        recipients=[email],
        body=html,
        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.post("/send-otp-email")
async def send_otp(current_password: str, db: AsyncSession = Depends(get_db), user: dict = Depends(auth.decode_token_user)):
    email = user.get("email")
    otp = await otp_service.create_otp(email=email)
    correct_password = await user_service.verify_password_user(email=email, password=current_password, db=db)
    if not correct_password:
        return {"status": "failed", "error": "Incorrect current password"}

    html = generate_email_html("otp", otp)

    message = MessageSchema(
        subject="CAREER - OTP Verification",
        recipients=[email],
        body=html,
        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.post("/send-email-forgot-password/{email}")
async def send_forgot_email(email: str, db: AsyncSession = Depends(get_db)):
    exist_user = await user_service.user_is_exist(email=email, db=db)
    if not exist_user:
        return {"status": "failed", "error": "Email not exist!"}

    token = auth.create_access_token(data={"name": "verify", "email": email}, expires_delta=timedelta(minutes=15))
    html = generate_email_html("forgot_password", token)

    message = MessageSchema(
        subject="CAREER - Reset your password",
        recipients=[email],
        body=html,
        subtype="html"
    )

    fm = FastMail(email_conf)
    try:
        await fm.send_message(message)
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
