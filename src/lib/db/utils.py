from ast import Tuple
from functools import wraps
from typing import Any, Callable, List
from pymongo.results import _WriteResult, InsertOneResult, InsertManyResult
from lib.abbot.exceptions.exception import try_except


def successful_update_one(result: _WriteResult) -> bool:
    return result.acknowledged == True


@try_except
def decorator_successful_update_one(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_update_one(func(*args, **kwargs))

    return wrapper


def successful_update_many(result: _WriteResult) -> bool:
    return result.acknowledged == True


@try_except
def decorator_successful_update_many(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_update_many(func(*args, **kwargs))

    return wrapper


def successful_insert_one(result: InsertOneResult) -> Tuple[Any, bool]:
    return (result.__inserted_id, result.acknowledged)


@try_except
def decorator_successful_insert_one(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_insert_one(func(*args, **kwargs))

    return wrapper


def successful_insert_many(result: InsertManyResult) -> bool:
    return result.acknowledged == True


@try_except
def decorator_successful_insert_many(func: Callable) -> bool:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return successful_insert_many(func(*args, **kwargs))

    return wrapper
