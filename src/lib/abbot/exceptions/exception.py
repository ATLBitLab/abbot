from functools import wraps
from lib.logger import bot_error
from traceback import format_exc, format_tb


class NostrEventNotFoundError(Exception):
    def __init__(self, kind=None, message="Nostr event not found", formatted_traceback=None, custom_stack=None):
        self.formatted_traceback = formatted_traceback
        self.custom_stack = custom_stack
        if kind is not None:
            message = f"Nostr event not found for kind: {kind}"
        super().__init__(message)


class AbbotException(Exception):
    def __init__(self, message, formatted_traceback=None, custom_stack=None):
        super().__init__(message)
        self.formatted_traceback = formatted_traceback
        self.custom_stack = custom_stack


def try_except(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            abbot_exception = AbbotException(exception, format_exc(), format_tb(exception.__traceback__)[:-1])
            bot_error.log(f"Error: {abbot_exception}")
            pass

    return wrapper


def try_except_raise(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            error_message = f"An error occurred: {exception}"
            abbot_exception = AbbotException(error_message, format_exc(), format_tb(exception.__traceback__)[:-1])
            bot_error.log(f"Error: {abbot_exception}")
            raise abbot_exception

    return wrapper
