from random import randrange
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from lib.abbot.config import BOT_RESPONSES

from ..utils import try_get
from constants import THE_CREATOR
from .exceptions.exception import try_except
from ..logger import debug_logger, error_logger

BASE_KEYS = ["text", "date"]


def successful(data: dict) -> bool:
    return data["status"] == "success"


def unsuccessful(data: dict) -> bool:
    return data["status"] != "success"


@try_except_pass
async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    fn = f"{get_chat_admins.__name__}:"
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    chat_admin_data = dict(ids=admin_ids, usernames=admin_usernames)
    debug_logger.log(f"{fn} chat_admin_data={chat_admin_data}")
    return chat_admin_data


@try_except_pass
def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None | Message:
    fn = f"{parse_message.__name__}:"
    message: Message = try_get(update, "message")
    if not message:
        error_message = f"{fn} No message: update={update.to_json()} context={context}"
        return dict(status="error", data=error_message)
    debug_logger.log(f"{fn} message={message}")
    return dict(status="success", data=message)


@try_except_pass
def parse_message_data(message: Message, keys: list = None, **kwargs) -> bool | dict:
    fn = f"{parse_message_data.__name__}:"
    if not keys:
        keys = BASE_KEYS
    additional_keys = kwargs.pop("keys", None)
    if additional_keys:
        keys = [*keys, *additional_keys]
    debug_logger.log(f"{fn} keys={keys}")
    message_data: dict = dict()
    for key in keys:
        message_data[key] = try_get(message, key, default="")
    debug_logger.log(f"{fn} message_data={message_data}")
    return message_data


@try_except_pass
def parse_chat(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None | Chat:
    fn = f"{parse_message_data.__name__}:"
    chat: Chat = try_get(message, "chat")
    if not chat:
        error_message = f"{fn} No message: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    debug_logger.log(f"{fn} chat={chat}")
    return dict(status="success", data=chat)


@try_except_pass
def parse_chat_data(chat: Chat) -> bool | dict:
    fn = f"{parse_chat_data.__name__}:"
    chat_id: int = try_get(chat, "id")
    chat_title: str = try_get(chat, "title")
    chat_type: str = try_get(chat, "type")
    chat_data = dict(id=chat_id, title=chat_title, type=chat_type)
    debug_logger.log(f"{fn} chat_data={chat_data}")
    return chat_data


@try_except_pass
def parse_user(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None | User:
    fn = f"{parse_user.__name__}:"
    user: User = try_get(message, "from_user")
    if not user:
        error_message = f"{fn} No message: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    debug_logger.log(f"{fn} {user}")
    return dict(status="success", data=user)


@try_except_pass
def parse_user_data(user: User) -> bool | dict:
    fn = f"{parse_user_data.__name__}:"
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    user_data = dict(user_id=user_id, username=username)
    debug_logger.log(f"{fn} {user_data}")
    return user_data


@try_except_pass
async def squawk_error(error_message: str, context: ContextTypes.DEFAULT_TYPE):
    fn = f"{squawk_error.__name__}:"
    error_logger.log(f"{fn} {error_message}")
    return await context.bot.send_message(chat_id=THE_CREATOR, text=error_message)


@try_except_pass
def get_bot_response(response_type: str, index: int = None) -> str:
    response_list = try_get(BOT_RESPONSES, response_type)
    index = randrange(len(response_list)) if not index else index
    return try_get(response_list, index)
