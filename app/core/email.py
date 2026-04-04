import os
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

class EmailSettings(BaseModel):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

# Read from environment variables
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "Tungdohotat12345@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "knyz iyfr jyqz ewdf")
MAIL_FROM = os.getenv("MAIL_FROM", "Tungdohotat12345@gmail.com")

# Validate required environment variables
if not MAIL_USERNAME or not MAIL_PASSWORD or not MAIL_FROM:
    raise RuntimeError(
        "Email configuration missing. Please set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_FROM "
        "in your environment or .env file."
    )

settings = EmailSettings(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True"),
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False")
)
