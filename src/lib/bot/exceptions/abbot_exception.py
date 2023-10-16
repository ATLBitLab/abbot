from functools import wraps
from traceback import extract_stack, format_exc
from lib.logger import error_logger


class AbbotException(Exception):
    def __init__(self, message, __traceback__=None, __stack__=None):
        super().__init__(message)
        self.__stack__ = __stack__
        self.__traceback__ = __traceback__


def try_except(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error_message = f"An error occurred: {exception}"
            custom_exception = AbbotException(error_message, format_exc(), extract_stack()[:-1])
            error_logger.log(f"Error: {custom_exception}")
            raise custom_exception

    return wrapper
