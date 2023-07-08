from lib.env import STRIKE_API_KEY

STRIKE_BASE_URL = "https://api.strike.me/v1"
STRIKE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {STRIKE_API_KEY}",
}

from requests import request
from datetime import datetime


def get_now():
    return datetime.now()


def get_now_date():
    return datetime.now().date()


def http_request(method, path, data=None):
    return request(
        method=method,
        url=f"{STRIKE_BASE_URL}/{path}",
        data=data,
        headers=STRIKE_HEADERS,
    )
