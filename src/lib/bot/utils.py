from traceback import extract_tb, extract_stack
from functools import wraps
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User
from lib.bot.config import ORG_CHAT_ID, ORG_CHAT_TITLE
from lib.bot.exceptions.AbbitException import try_except
from lib.utils import try_get, try_gets
from lib.logger import debug_logger, error_logger
from datetime import datetime

now = datetime.now().date()


async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    return dict(ids=admin_ids, usernames=admin_usernames)


def deconstruct_error(error):
    return try_gets(error, keys=["__cause__", "__traceback__", "args"])


def parse_message(update: Update) -> Message:
    fn = "parse_message =>"
    try:
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        if not message:
            debug_logger.log(f"{fn} no message data: {message}")
            return False
        return message
    except Exception as exception:
        error_logger.log(f"{fn} Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"{fn} Error={exception}, ErrorMessage={error_msg}")
        raise exception


BASE_KEYS = ["text", "date"]


@try_except
def parse_message_data(
    message: Message, keys: list = BASE_KEYS, **kwargs
) -> bool | dict:
    fn = "parse_message_data =>"
    additional_keys = kwargs.pop("keys", None)
    if additional_keys:
        keys = [*keys, *additional_keys]
    message_data = {
        f"{key}: ${(try_get(message, key) or now).strftime('%m/%d/%Y')}"
        if key == "date"
        else f"{key}: ${try_get(message, key)}"
        for key in keys
        if key != "date"
    }
    if len(message_data) < len(keys):
        debug_logger.log(f"{fn} parsed values < number of keys: {message_data}")
        return False
    return message_data


def parse_chat(update: Update, message: Message) -> Chat:
    fn = "parse_chat =>"
    try:
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        if not chat:
            debug_logger.log(f"{fn} no chat data: {chat}")
            return False
        return chat
    except Exception as exception:
        error_logger.log(f"{fn} Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"{fn} Error={exception}, ErrorMessage={error_msg}")
        raise exception


def parse_chat_data(chat: Chat) -> bool | dict:
    fn = "parse_chat_data =>"
    try:
        chat_id: int = try_get(chat, "chat_id") or ORG_CHAT_TITLE
        chat_title: str = try_get(chat, "title") or ORG_CHAT_ID
        return dict(chat_id=chat_id, chat_title=chat_title)
    except Exception as exception:
        error_logger.log(f"{fn} Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"{fn} Error={exception}, ErrorMessage={error_msg}")
        raise exception


def parse_user(message: Message) -> User:
    fn = "parse_user =>"
    try:
        user: User = try_get(message, "from_user")
        if not user:
            error_logger.log(f"start => Missing User: {user}")
            return False
        return user
    except Exception as exception:
        error_logger.log(f"{fn} Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"{fn} Error={exception}, ErrorMessage={error_msg}")
        raise exception


def parse_user_data(user: User) -> bool | dict:
    fn = "parse_user_data =>"
    try:
        user_id: int = try_get(user, "id")
        username: int = try_get(user, "username")
        if not user or not username:
            error_logger.log(f"{fn} no user_id: {user_id}")
            error_logger.log(f"{fn} no username: {username}")
            return False
        return dict(user_id=user_id, username=f"@{username}")
    except Exception as exception:
        error_logger.log(f"{fn} Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"{fn} Error={exception}, ErrorMessage={error_msg}")
        raise exception
