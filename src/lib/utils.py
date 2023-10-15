import json
from requests import request
from datetime import datetime, timedelta
from qrcode import make
from io import BytesIO
from bot_constants import OPT_INOUT_FILE, OPT_INOUT_FILEPATH
from lib.logger import debug_logger

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


def get_dates(lookback=7):
    return [
        (
            (datetime.now() - timedelta(days=1)).date() - timedelta(days=i - 1)
        ).isoformat()
        for i in range(lookback, 0, -1)
    ]


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
    qr = make(data)
    bio = BytesIO()
    qr.save(bio, "PNG")
    bio.seek(0)
    return bio


def opt_in(context: str, chat_id: int) -> bool:
    fn = "opt_in => "
    optinout_list: list = OPT_INOUT_FILE[context]
    if chat_id not in optinout_list:
        debug_logger.log(f"{fn} chat_id={chat_id} opting in")
        optinout_list.append(chat_id)
        json.dump(OPT_INOUT_FILE, OPT_INOUT_FILEPATH, indent=4)
    return True


def opt_out(context: str, chat_id: int) -> bool:
    fn = "opt_out =>"
    optinout_list: list = OPT_INOUT_FILE[context]
    if chat_id in optinout_list:
        debug_logger.log(f"{fn} chat_id={chat_id} opting out")
        optinout_list.remove(chat_id)
        json.dump(OPT_INOUT_FILE, OPT_INOUT_FILEPATH, indent=4)
    return True
