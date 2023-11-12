from functools import wraps
from typing import Callable
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult

from lib.utils import try_get


def successful_update_one(result: UpdateResult) -> bool:
    return try_get(result, "acknowledged") == True


def decorator_successful_update_one(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_update_one(func(*args, **kwargs))

    return wrapper


def successful_update_many(result: UpdateResult) -> bool:
    return try_get(result, "acknowledged") == True


def decorator_successful_update_many(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_update_many(func(*args, **kwargs))

    return wrapper


def successful_insert_one(result: InsertOneResult) -> bool:
    return try_get(result, "inserted_id") != None and try_get(result, "acknowledged") == True


def decorator_successful_insert_one(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_insert_one(func(*args, **kwargs))

    return wrapper


def successful_insert_many(result: InsertManyResult) -> bool:
    return try_get(result, "acknowledged") == True


def decorator_successful_insert_many(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_insert_many(func(*args, **kwargs))

    return wrapper
