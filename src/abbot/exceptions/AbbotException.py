from functools import wraps
from traceback import extract_stack, format_exc
from lib.logger import error_logger


class AbbitException(Exception):
    def __init__(self, message, __traceback__=None, __stack__=None):
        super().__init__(message)
        self.__stack__ = __stack__
        self.__traceback__ = __traceback__


def try_except(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AbbitException as exception:
            stack_data = extract_stack()[:-1]
            traceback_info = format_exc()
            error_message = f"AbbitException: {exception}"
            custom_exception = AbbitException(error_message, stack_data, traceback_info)
            error_logger.log(custom_exception)
            raise custom_exception

    return wrapper
