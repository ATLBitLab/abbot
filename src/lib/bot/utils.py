from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User
from .config import ORG_CHAT_ID, ORG_CHAT_TITLE
from .exceptions.abbot_exception import AbbotException, try_except
from lib.utils import try_get, try_gets
from lib.logger import debug_logger, error_logger
from datetime import datetime

BASE_KEYS = ["text", "date"]


@try_except
async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    return dict(ids=admin_ids, usernames=admin_usernames)


@try_except
def parse_message(update: Update) -> Message:
    fn = "parse_message =>"
    message: Message = try_get(update, "message") or try_get(update, "effective_message")
    if not message:
        debug_logger.log(f"{fn} no message data: {message}")
        return False
    return message


@try_except
def parse_message_data(message: Message, keys: list, **kwargs) -> bool | dict:
    fn = "parse_message_data =>"
    if not keys:
        keys = BASE_KEYS
    additional_keys = kwargs.pop("keys", None)
    if additional_keys:
        keys = [*keys, *additional_keys]
    message_data = {
        f"{key}: ${(try_get(message, key, default=datetime.now())).strftime('%m/%d/%Y')}"
        if key == "date"
        else f"{key}: ${try_get(message, key)}"
        for key in keys
        if key != "date"
    }
    if len(message_data) < len(keys):
        debug_logger.log(f"{fn} parsed values < number of keys: {message_data}")
        return False
    return message_data


@try_except
def parse_chat(update: Update, message: Message) -> Chat:
    fn = "parse_chat =>"
    chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
    if not chat:
        debug_logger.log(f"{fn} no chat data: {chat}")
        return False
    return chat


@try_except
def parse_chat_data(chat: Chat) -> bool | dict:
    fn = "parse_chat_data =>"
    debug_logger.log(fn)
    chat_id: int = try_get(chat, "chat_id") or ORG_CHAT_TITLE
    chat_title: str = try_get(chat, "title") or ORG_CHAT_ID
    return dict(chat_id=chat_id, chat_title=chat_title)


@try_except
def parse_user(message: Message) -> User:
    fn = "parse_user =>"
    debug_logger.log(fn)
    user: User = try_get(message, "from_user")
    if not user:
        error_logger.log(f"start => Missing User: {user}")
        return False
    return user


@try_except
def parse_user_data(user: User) -> bool | dict:
    fn = "parse_user_data =>"
    debug_logger.log(fn)
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    if not user or not username:
        error_logger.log(f"{fn} no user_id: {user_id}")
        error_logger.log(f"{fn} no username: {username}")
        return False
    return dict(user_id=user_id, username=f"@{username}")
