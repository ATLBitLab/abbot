from functools import wraps
from lib.logger import error_logger
from traceback import format_exc, format_tb


class AbbotException(Exception):
    def __init__(self, message, formatted_traceback=None, custom_stack=None):
        super().__init__(message)
        self.formatted_traceback = formatted_traceback
        self.custom_stack = custom_stack


def try_except_pass(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error_message = f"An error occurred: {exception}"
            abbot_exception = AbbotException(error_message, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_logger.log(f"Error: {abbot_exception}")
            pass

    return wrapper


def try_except(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error_message = f"An error occurred: {exception}"
            abbot_exception = AbbotException(error_message, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_logger.log(f"Error: {abbot_exception}")
            return abbot_exception

    return wrapper


def try_except_raise(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error_message = f"An error occurred: {exception}"
            abbot_exception = AbbotException(error_message, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_logger.log(f"Error: {abbot_exception}")
            raise abbot_exception

    return wrapper
