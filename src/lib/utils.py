from functools import wraps
import json
from io import open
from logging import debug
import traceback
from requests import request
from datetime import datetime, timedelta
from qrcode import make
from io import BytesIO
from bot_constants import OPTIN_OUT_FILE, OPTINOUT_FILEPATH
from lib.logger import error

TELEGRAM_MESSAGE_FIELDS = [
    "audio",
    "document",
    "game",
    "photo",
    "sticker",
    "video",
    "voice",
    "video_note",
    "caption",
]


def try_except(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        fn = "try_except => wrapper =>"
        try:
            # ---- Success ----
            return fn(*args, **kwargs)
        except Exception as exception:
            error(f"{fn} exception={exception}")
            raise

    return wrapper


def now_date():
    return datetime.now().date()


@try_except
def get_dates(lookback=7):
    return [
        (
            (datetime.now() - timedelta(days=1)).date() - timedelta(days=i - 1)
        ).isoformat()
        for i in range(lookback, 0, -1)
    ]


@try_except
def try_set(obj, value, *keys, **kwargs):
    default = kwargs.pop("default", None)
    if kwargs:
        unexpected_kw = kwargs[kwargs.keys()[0]]
        raise TypeError("try_set received unexpected keyword argument", unexpected_kw)
    for key in keys:
        try:
            obj[key] = value
        except (AttributeError, KeyError, TypeError, IndexError):
            try:
                obj = getattr(obj, key)
            except Exception:
                return default
    return obj


@try_except
def try_get(obj, *fields, **kwargs):
    default = kwargs.pop("default", None)
    if kwargs:
        unexpected_kw = kwargs[kwargs.keys()[0]]
        raise TypeError("try_get received unexpected keyword argument", unexpected_kw)
    for field in fields:
        try:
            obj = obj[field]
        except (AttributeError, KeyError, TypeError, IndexError):
            try:
                obj = getattr(obj, field)
            except Exception:
                return default
    return obj


@try_except
def try_get_telegram_message_data(telegram_message):
    return {f"{key}": try_get(telegram_message, key) for key in TELEGRAM_MESSAGE_FIELDS}


@try_except
def try_gets(obj, keys=[], return_type="list", **kwargs):
    additional_keys = kwargs.pop("keys", None)
    keys = [*keys, *additional_keys] if additional_keys else keys
    return (
        [try_get(obj, key, kwargs) for key in keys]
        if return_type == "list"
        else {f"{key}": try_get(obj, key, kwargs) for key in keys}
    )


@try_except
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


@try_except
def qr_code(data):
    qr = make(data)
    bio = BytesIO()
    qr.save(bio, "PNG")
    bio.seek(0)
    return bio


@try_except
def opt_in(context: str, chat_id: int) -> bool:
    fn = "opt_in => "
    optinout_list = OPTIN_OUT_FILE[context]
    if chat_id not in optinout_list:
        debug(f"{fn} chat_id={chat_id} opting in")
        optinout_list.append(chat_id)
        json.dump(OPTIN_OUT_FILE, OPTINOUT_FILEPATH, indent=4)
    return True


@try_except
def opt_out(context: str, chat_id: int) -> bool:
    fn = "opt_out =>"
    optinout_list = OPTIN_OUT_FILE[context]
    if chat_id in optinout_list:
        debug(f"{fn} chat_id={chat_id} opting out")
        optinout_list.remove(chat_id)
        json.dump(OPTIN_OUT_FILE, OPTINOUT_FILEPATH, indent=4)
    return True
