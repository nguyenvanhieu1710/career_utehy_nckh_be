from app.core import momo
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, engine, SessionLocal
from app.utils import auth, payment
from app.services import paypal_service, oder_service

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/momo/create")
def momo_create(data: payment.PackPayload, user_id: str = Depends(auth.verify_token_user)):
    momo_res = momo.create(data=data, user_id=user_id)
    return momo_res


@router.post("/paypal/create")
def paypal_create(pack: payment.PackPayload, user_id: str = Depends(auth.verify_token_user)):
    res = paypal_service.create_order(pack=pack.pack, user_id=user_id)
    return res

@router.post("/paypal/capture")
async def paypal_capture(order_id: str, order_token:str, db: AsyncSession=Depends(get_db)):
    res = paypal_service.capture_order(order_id=order_id)
    if res["status"] == 'COMPLETED':
       order_res = await oder_service.create(pay_token=order_token, db=db)
       return order_res
    return res

