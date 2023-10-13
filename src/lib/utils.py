import json
from io import open
from requests import request
from datetime import datetime, timedelta
from qrcode import make
from io import BytesIO
from lib.logger import error_logger

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


# keys=["__cause__", "__traceback__", "args"]
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


def update_optin_optout(
    file_path: str, context: str, chat_id: int, opt_in: bool
) -> bool:
    try:
        """
        Update the JSON file at `file_path` by adding `chat_id` to the array associated with `context`.
        """
        # Read the existing data
        optinout_data = json.load(open(file_path, "r"))

        # Add the new value to the appropriate context
        change_made = False
        optinout_list = optinout_data[context]
        if opt_in and chat_id not in optinout_list:
            optinout_list.append(chat_id)
            change_made = True
        elif not opt_in and chat_id in optinout_list:
            optinout_list.remove(chat_id)
            change_made = True

        # Write the updated optinout_data back to the file
        if change_made:
            with open(file_path, "w") as file:
                json.dump(optinout_data, file, indent=4)

        return True
    except Exception as exception:
        error_logger.log(f"context {context} not found in optinout_data.")
        raise exception
