from requests import request
from datetime import datetime


def get_now():
    return datetime.now()


def get_now_date():
    return datetime.now().date()


def http_request(headers, method, url, path, json=None):
    return request(
        headers=headers,
        method=method,
        url=f"{url}/{path}",
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
