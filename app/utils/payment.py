from app.utils import auth
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel


class PackPayload(BaseModel):
    pack: str


def get_amount(pack: str, money_code: str):
    if (money_code == 'VND'):
        if pack == 'month':
            
            return 12906
        elif pack == 'year':
            return 134597
        elif pack == 'life':
            return 790200
    elif (money_code == "USD"):
        if pack == 'month':
            return 0.49
        elif pack == 'year':
            return 5.11
        elif pack == 'life':
            return 30
        
def create_order_token(pack:str, money_code:str, user_id: str):
    oid = uuid.uuid4()
    a = get_amount(pack=pack, money_code=money_code)
    return auth.create_access_token(data={
    "order_id": str(oid),
    "pack" : pack,
    "amount": a,
    "user_id": user_id
    }, expires_delta=timedelta(minutes=5))