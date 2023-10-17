import json
from functools import wraps
from logging import debug
from requests import request
from os.path import abspath
from qrcode import make
from io import BytesIO
from .logger import error

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
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error(f"try_except => exception={exception}")
            raise

    return wrapper


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
    fn = "opt_in:"
    config_file_name = f"src/data/chat/{context}/config/{chat_id}.json"
    debug(f"{fn} config_file_name={config_file_name}")
    config_file_path = abspath(config_file_name)
    with open(config_file_path, 'w') as config:
        json.dump({"started": True, "sent_intro": False}, config)
    return True


def opt_out(context: str, chat_id: int) -> bool:
    fn = "opt_out:"
    config_file_name = f"src/data/chat/{context}/config/{chat_id}.json"
    debug(f"{fn} config_file_name={config_file_name}")
    config_file_path = abspath(config_file_name)
    with open(config_file_path, 'w') as config:
        json.dump({"started": False, "sent_intro": True}, config)
    return True