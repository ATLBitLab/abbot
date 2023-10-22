from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from ..utils import try_get
from constants import THE_CREATOR
from .exceptions.abbot_exception import try_except
from ..logger import debug_logger, error_logger

BASE_KEYS = ["text", "date"]


def successful(data: dict) -> bool:
    return data["status"] == "success"


def unsuccessful(data: dict) -> bool:
    return data["status"] != "success"


@try_except
async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    return dict(ids=admin_ids, usernames=admin_usernames)


@try_except
def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None | Message:
    fn = "parse_message:"
    message: Message = try_get(update, "message")
    debug_logger.log(f"{fn} Message={message}")
    if not message:
        error_message = f"{fn} No message: update={update.to_json()} context={context}"
        return dict(status="error", data=error_message)
    return dict(status="success", data=message)


@try_except
def parse_message_data(message: Message, keys: list = None, **kwargs) -> bool | dict:
    fn = "parse_message_data:"
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


@try_except
def parse_chat(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None | Chat:
    fn = "parse_chat:"
    chat: Chat = try_get(message, "chat")
    debug_logger.log(f"{fn} Chat={chat}")
    if not chat:
        error_message = f"{fn} No message: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    return dict(status="success", data=chat)


@try_except
def parse_chat_data(chat: Chat) -> bool | dict:
    fn = "parse_chat_data:"
    debug_logger.log(f"{fn} chat={chat.to_dict()}")
    chat_id: int = try_get(chat, "id")
    chat_title: str = try_get(chat, "title")
    chat_type: str = try_get(chat, "type")
    return dict(id=chat_id, title=chat_title, type=chat_type)


@try_except
def parse_user(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None | User:
    fn = "parse_user:"
    debug_logger.log(fn)
    user: User = try_get(message, "from_user")
    if not user:
        error_message = f"{fn} No message: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    return dict(status="success", data=user)


@try_except
def parse_user_data(user: User) -> bool | dict:
    fn = "parse_user_data:"
    debug_logger.log(fn)
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    return dict(user_id=user_id, username=username)


@try_except
async def squawk_error(error_message: str, context: ContextTypes.DEFAULT_TYPE):
    if error_message:
        error_logger.log(error_message)
        return await context.bot.send_message(chat_id=THE_CREATOR, text=error_message)
