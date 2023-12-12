from functools import wraps
from lib.logger import error_bot, debug_bot
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
            except_msg = f"{__name__}: {exception}"
            abbot_exception = AbbotException(except_msg, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_bot.log(__name__, abbot_exception)
            pass

    return wrapper


def try_except_raise(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exception:
            abbot_exception = AbbotException(exception, format_exc(), format_tb(exception.__traceback__)[:-1])
            error_bot.log(f"try_except: {abbot_exception}")
            return abbot_exception

    return wrapper


def log_me(fn):
    return log_me_if(lambda: True)(fn)


def log_me_if(predicate):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = func(*args, **kwargs)
            if predicate(r):
                debug_bot.log()
            return r

        return wrapper

    return decorator
