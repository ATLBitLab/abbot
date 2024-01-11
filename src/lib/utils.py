import json

from functools import wraps
from typing import Dict
from httpx import Response

from qrcode import make
from os.path import abspath
from io import BytesIO, open
from requests import request

from telegram.ext import ContextTypes
from lib.logger import debug_bot

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
FILE_NAME = __name__


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


def try_dumps(data: Dict, **kwargs) -> Dict:
    if type(data) != dict:
        return error("Data is not dict", data=data)
    try:
        data_dump = json.dumps(data, indent=4)
        return success("Success data dumped", data=data_dump)
    except:
        return error("Data is not dict", data=data)


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
    log_name = f"{FILE_NAME}: opt_in"
    config_file_name = f"src/data/chat/{context}/config/{chat_id}.json"
    debug_bot.log(log_name, f"config_file_name={config_file_name}")
    config_file_path = abspath(config_file_name)
    with open(config_file_path, "w") as config:
        json.dump({"started": True, "sent_intro": False}, config)
    return True


def opt_out(context: str, chat_id: int) -> bool:
    log_name = f"{FILE_NAME}: opt_out"
    config_file_name = f"src/data/chat/{context}/config/{chat_id}.json"
    debug_bot.log(log_name, f"config_file_name={config_file_name}")
    config_file_path = abspath(config_file_name)
    with open(config_file_path, "w") as config:
        json.dump({"started": False, "sent_intro": True}, config)
    return True


async def sender_is_group_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in admins]
    return user_id in admin_ids


def json_loader(filepath: str, key: str | None = None, mode: str = "r"):
    json_data = json.load(open(abspath(filepath), mode))
    return try_get(json_data, key) if key else json_data


def to_dict(cls):
    def to_dict(self):
        return vars(self)

    setattr(cls, "to_dict", to_dict)
    return cls


"""
def to_dict(cls):
    print("to_dict")
    cls_name = f"{cls.__name__}: @to_dict: "
    if hasattr(cls, "to_dict"):
        error_bot.log("", f"{cls_name}", f"already has method 'to_dict'")
        return

    def to_dict(self):
        self_dict: Dict = vars(self)
        result = {}
        for key, val in self_dict.items():
            if hasattr(val, "to_dict") and callable(val.to_dict):
                result[key] = val.to_dict()
            else:
                result[key] = val
        return result

    setattr(cls, "to_dict", to_dict)
    return cls
"""


def fn_name(fn):
    @wraps(fn)
    def wrapper():
        return fn.__name__

    return wrapper


def error(msg: str = "", **kwargs) -> Dict:
    return dict(status="error", msg=msg, **kwargs)


def success(msg: str = "", **kwargs):
    return dict(status="success", msg=msg, **kwargs)


def successful(response: Dict) -> bool:
    return response["status"] == "success"


def successful_response(response: Response) -> bool:
    return response.status_code == 200


def unsuccessful(response: Dict) -> bool:
    return not successful(response)
