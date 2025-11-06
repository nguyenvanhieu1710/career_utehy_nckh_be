from pydantic import BaseModel, EmailStr

class EmailSettings(BaseModel):
    MAIL_USERNAME: str = "Tungdohotat12345@gmail.com"
    MAIL_PASSWORD: str = "knyz iyfr jyqz ewdf"
    MAIL_FROM: EmailStr = "Tungdohotat12345@gmail.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

settings = EmailSettings()
