from functools import wraps
import json
from typing import Any, Callable, Dict

from qrcode import make
from os.path import abspath
from io import BytesIO, open
from requests import request

from telegram.ext import ContextTypes
from lib.logger import bot_debug, bot_error
from lib.abbot.exceptions.exception import try_except


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
    bot_debug.log(f"{fn} config_file_name={config_file_name}")
    config_file_path = abspath(config_file_name)
    with open(config_file_path, "w") as config:
        json.dump({"started": True, "sent_intro": False}, config)
    return True


def opt_out(context: str, chat_id: int) -> bool:
    fn = "opt_out:"
    config_file_name = f"src/data/chat/{context}/config/{chat_id}.json"
    bot_debug.log(f"{fn} config_file_name={config_file_name}")
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


def error(message: str = "", **kwargs) -> Dict:
    return {"status": "error", "message": message, **kwargs}


def success(message: str = "", **kwargs) -> dict:
    return {"status": "success", "message": message, **kwargs}


def successful(response: dict) -> bool:
    return response["status"] == "success"


def unsuccessful(response: dict) -> bool:
    return not successful(response)
