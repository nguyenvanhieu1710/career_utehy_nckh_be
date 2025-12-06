import requests
import base64
import os
import logging
from app.utils import auth, payment

logger = logging.getLogger(__name__)

PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")


def get_access_token():
    client_id = os.getenv("PAYPAL_CLIENT_ID", "AZJM416AJv3dwgYx3N9PK0NADEaYR_Gx0Y2rlP-3Sgrxs3njBp_AI25hsVogBMnsjVGcn24poaH3NusY")
    client_secret = os.getenv("PAYPAL_SECRET", "ELPXKEhIiWPcTeq7Q4k7LeA55Ynude3gzSlTYk9hdtkjDMXZPxi8vOkCx3Yoq2OKKb9mtOYkzzWy7MVk")
    if not client_id or not client_secret:
        raise RuntimeError("PayPal configuration missing. Please set PAYPAL_CLIENT_ID and PAYPAL_SECRET environment variables")

    auth_str = f"{client_id}:{client_secret}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    resp = requests.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def create_order(pack: str, user_id: str):
    access_token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": payment.get_amount(pack=pack, money_code="USD")
                }
            }
        ],
        "application_context": {
            "return_url": f"http://localhost:3000/paypal-success/{payment.create_order_token(pack=pack, money_code='USD', user_id=user_id)}",
            "cancel_url": "http://localhost:3000/"
        }
    }

    resp = requests.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders", headers=headers, json=body)
    resp.raise_for_status()
    order = resp.json()

    # Lấy link approve cho user redirect
    approve_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
    return {"order_id": order["id"], "approve_url": approve_url}


def capture_order(order_id: str):
    access_token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        resp = requests.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
            headers=headers
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        error_data = None
        try:
            error_data = resp.json()
        except Exception:
            error_data = resp.text
        logger.exception("PayPal capture failed: %s", order_id)
        return {"status": "FAILURE", "error": str(e), "details": error_data}

    return resp.json()
