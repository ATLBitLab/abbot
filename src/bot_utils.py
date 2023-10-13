from functools import wraps
from random import randrange
from telegram import Message, Update, Chat, User
from constants import CHEEKY_RESPONSES, SUPER_DOOPER_ADMINS

from lib.utils import try_get, try_gets
from lib.logger import debug_logger, error_logger
from datetime import datetime

now = datetime.now().date()


def rand_num():
    return randrange(len(CHEEKY_RESPONSES))


def trycatch(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # ---- Success ----
            return fn(*args, **kwargs)
        except Exception as error:
            debug_logger.log(f"abbot => /prompt Error: {error}")
            raise error

    return wrapper


def whitelist_gate(sender):
    return sender not in SUPER_DOOPER_ADMINS


def deconstruct_error(error):
    return try_gets(error, keys=["__cause__", "__traceback__", "args"])


def parse_update(update: Update) -> (Message, Chat, User):
    try:
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        user: User = try_get(message, "from_user")
        if not message:
            debug_logger.log(f"start => Missing Message: {message}")
            return False, message
        if not chat:
            error_logger.log(f"start => Missing Chat: {chat}")
            return False, message, chat
        if not user:
            error_logger.log(f"start => Missing User: {user}")
            return False, message, chat, user
        return True, message, chat, user
    except Exception as exception:
        error_logger.log(f"parse_update => Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"parse_update => Error={exception}, ErrorMessage={error_msg}")
        raise exception


def parse_update_data(message: Message, chat: Chat, user: User):
    try:
        text: str = try_get(message, "text")
        date = (try_get(message, "date") or now).strftime("%m/%d/%Y")
        user_id: int = try_get(user, "id")
        username: int = try_get(user, "username")
        if not text:
            error_logger.log(f"parse_update_data => text={text}")
            return False, text
        if not date:
            error_logger.log(f"parse_update_data => date={date}")
            return False, text, date
        if not user_id:
            error_logger.log(f"parse_update_data => user_id={user_id}")
            return False, text, user_id
        if not username:
            error_logger.log(f"parse_update_data => username={username}")
            return False, text, user_id, username
        return True, text, user_id, username
    except Exception as exception:
        error_logger.log(f"parse_update_data => Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(
            f"parse_update_data => Error={exception}, ErrorMessage={error_msg}"
        )
        raise exception
