from os.path import abspath
import logging

logger = logging.getLogger("atl_bitlab_bot")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(abspath("data/debug.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

from constants import TELEGRAM_MESSAGE_FIELDS
from requests import request
from datetime import datetime, timedelta
import qrcode
from io import BytesIO


def now_date():
    return datetime.now().date()


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
    msg_formatted = f"[{now_date()}] {__name__}: {msg}\n"
    print(msg_formatted)
    logger.debug(msg_formatted)


def error(message="", **kwargs):
    data = {"status": "error", "message": message}
    for key in kwargs.keys():
        data[key] = kwargs[key]
    debug(f"Error: {data}")
    return data


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


def try_get_telegram_message_data(telegram_message):
    return {f"{key}": try_get(telegram_message, key) for key in TELEGRAM_MESSAGE_FIELDS}


def try_gets(obj, keys=[], return_type="list", **kwargs):
    additional_keys = kwargs.pop("keys", None)
    keys = [*keys, *additional_keys] if additional_keys else keys
    return (
        [try_get(obj, key, kwargs) for key in keys]
        if return_type == "list"
        else {f"{key}": try_get(obj, key, kwargs) for key in keys}
    )


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
