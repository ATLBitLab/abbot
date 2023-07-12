from requests import request
from datetime import datetime
import qrcode
from io import BytesIO


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


def get_now():
    return datetime.now()


def get_now_date():
    return datetime.now().date()


def http_request(headers, method, url, json=None):
    return request(
        headers=headers,
        method=method,
        url=url,
        json=json,
    ).json()


"""
TODO:
- [ ] abstract the payment method for FOSS users
      allow users to plug in any number of LN / BTC payment methods
      e.g home node (LND, CLN, etc)
      cloud node (voltage, aws, etc)
      LSPs (stike, opennode, etc.)
"""
