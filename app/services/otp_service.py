import random, string, hashlib, time
import asyncio
from redis.asyncio import Redis

redis = Redis(host="localhost", port=6379, db=0)

OTP_EXPIRE_SECONDS = 60 

def generate_otp(length=5):
    return ''.join(random.choices(string.digits, k=length))

async def create_otp(email: str):
    otp = generate_otp()
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    key = f"otp:{email}"
    await redis.setex(key, OTP_EXPIRE_SECONDS, otp_hash)
    return otp

async def verify_otp(email: str, otp_input: str):
    key = f"otp:{email}"
    otp_hash = await redis.get(key)
    if not otp_hash:
        return False 
    otp_hash = otp_hash.decode()
    if otp_hash == hashlib.sha256(otp_input.encode()).hexdigest():
        await redis.delete(key) 
        return True
    return False
