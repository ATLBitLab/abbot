import os
import logging

from requests import request
from datetime import datetime, timedelta
import qrcode
from io import BytesIO

from constants import PROGRAM

logger = logging.getLogger("atl_bitlab_bot")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.abspath("data/debug.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def try_get(obj, *fields, **kwargs):
    default = kwargs.pop("default", None)
    if kwargs:
        raise TypeError(
            "try_get() received unexpected keyword argument", kwargs[kwargs.keys()[0]]
        )
    for field in fields:
        try:
            obj = obj[field]
        except (AttributeError, KeyError, TypeError, IndexError):
            try:
                obj = getattr(obj, field)
            except Exception:
                return default
    return obj


def now_date():
    return datetime.now().date()


def http_request(headers, method, url, json=None):
    try:
        return request(
            headers=headers,
            method=method,
            url=url,
            json=json,
        ).json()
    except Exception as e:
        return Exception(f"Request Failed: {e}")


def qr_code(data):
    qr = qrcode.make(data)
    bio = BytesIO()
    qr.save(bio, "PNG")
    bio.seek(0)
    return bio


def get_dates(lookback=7):
    return [
        (
            (datetime.now() - timedelta(days=1)).date() - timedelta(days=i - 1)
        ).isoformat()
        for i in range(lookback, 0, -1)
    ]


def get_logger():
    return logger


def debug(msg):
    msg_formatted = f"[{now_date()}] {PROGRAM}: {msg}\n"
    print(msg_formatted)
    logger.debug(msg_formatted)
