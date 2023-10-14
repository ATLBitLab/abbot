from functools import wraps
from traceback import extract_stack
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
        except Exception as exception:
            stack_data = extract_stack()[:-1]  # Exclude the current frame
            traceback_info = format_exc()
            error_message = f"An error occurred: {exception}"
            custom_exception = CustomException(
                error_message, stack_data, traceback_info
            )
            error_logger.log(f"Error: {custom_exception}")
            raise custom_exception

    return wrapper
