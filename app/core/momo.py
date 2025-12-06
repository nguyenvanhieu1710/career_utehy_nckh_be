import json
import uuid
import requests
import hmac
import hashlib
import os
import logging
from app.utils import auth, payment
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def create(data: payment.PackPayload, user_id: str):
    oid = uuid.uuid4()
    a = 0
    if data.pack == 'month':
        a = 12906
    elif data.pack == 'year':
        a = 134597
    elif data.pack == 'life':
        a = 790200
    # Read sensitive config from environment variables
    MOMO_ENDPOINT = os.getenv("MOMO_ENDPOINT", "https://test-payment.momo.vn/v2/gateway/api/create")
    accessKey = os.getenv("MOMO_ACCESS_KEY", "F8BBA842ECF85")
    secretKey = os.getenv("MOMO_SECRET_KEY", "K951B6PE1waDMi640xX08PD3vg6EkVlz")
    partnerCode = os.getenv("MOMO_PARTNER_CODE", "MOMO")
    ipnUrl = os.getenv("MOMO_IPN_URL", "https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b")
    redirect_base = os.getenv("MOMO_REDIRECT_BASE", "http://localhost:3000")

    if not accessKey or not secretKey or not partnerCode:
        raise RuntimeError("Momo configuration missing. Please set MOMO_ACCESS_KEY, MOMO_SECRET_KEY and MOMO_PARTNER_CODE environment variables")

    token = auth.create_access_token(data={
        "order_id": str(oid),
        "pack" : data.pack,
        "amount": a,
        "user_id": user_id
    }, expires_delta=timedelta(minutes=5))
    # Do not log token or other sensitive information
    redirectUrl = f"{redirect_base}/pay-success/{token}"
    endpoint = MOMO_ENDPOINT
    amount = a
    orderId = str(oid)
    requestId = str(uuid.uuid4())
    extraData = ""  # pass empty value or Encode base64 JsonString
    partnerName = "MoMo Payment"
    orderInfo = "pay with MoMo"
    requestType = "payWithMethod"
    storeId = "Test Store"
    orderGroupId = ""
    autoCapture = True
    lang = "vi"
    orderGroupId = ""

    # before sign HMAC SHA256 with format: accessKey=$accessKey&amount=$amount&extraData=$extraData&ipnUrl=$ipnUrl
    # &orderId=$orderId&orderInfo=$orderInfo&partnerCode=$partnerCode&redirectUrl=$redirectUrl&requestId=$requestId
    # &requestType=$requestType
    rawSignature = "accessKey=" + accessKey + "&amount=" + str(amount) + "&extraData=" + extraData + "&ipnUrl=" + ipnUrl + "&orderId=" + orderId \
                + "&orderInfo=" + orderInfo + "&partnerCode=" + partnerCode + "&redirectUrl=" + redirectUrl\
                + "&requestId=" + requestId + "&requestType=" + requestType

    # puts raw signature
    # signature
    h = hmac.new(bytes(secretKey, 'ascii'), bytes(rawSignature, 'ascii'), hashlib.sha256)
    signature = h.hexdigest()

    # json object send to MoMo endpoint

    data = {
        'partnerCode': partnerCode,
        'orderId': orderId,
        'partnerName': partnerName,
        'storeId': storeId,
        'ipnUrl': ipnUrl,
        'amount': amount,
        'lang': lang,
        'requestType': requestType,
        'redirectUrl': redirectUrl,
        'autoCapture': autoCapture,
        'orderInfo': orderInfo,
        'requestId': requestId,
        'extraData': extraData,
        'signature': signature,
        'orderGroupId': orderGroupId
    }
    data = json.dumps(data)
    clen = len(data)
    try:
        response = requests.post(endpoint, data=data, headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.exception("Momo payment request failed for OrderID[%s]", orderId)
        raise

    logger.info("Payment with Momo: OrderID[%s] created", orderId)
    return response.json()
