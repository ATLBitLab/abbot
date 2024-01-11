from functools import wraps
from lib.logger import error_bot, debug_bot
from traceback import format_exc, format_tb

FILE_NAME = __name__


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
    log_name = f"{FILE_NAME}: try_except"

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            abbot_exception = AbbotException(exception, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_bot.log(log_name, abbot_exception)
            pass

    return wrapper


def try_except_raise(fn):
    log_name = f"{FILE_NAME}: try_except_raise"

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            abbot_exception = AbbotException(exception, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_bot.log(log_name, f"try_except: {abbot_exception}")
            return abbot_exception

    return wrapper


def log_me(fn):
    return log_me_if(lambda: True)(fn)


def log_me_if(predicate):
    log_name = f"{FILE_NAME}: log_me_if"

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = func(*args, **kwargs)
            if predicate(r):
                debug_bot.log(log_name, r)
            return r

        return wrapper

    return decorator
