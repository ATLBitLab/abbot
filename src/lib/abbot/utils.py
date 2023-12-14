import tiktoken

from typing import Dict, List
from random import randrange
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from constants import OPENAI_MODEL, THE_CREATOR

from ..utils import success, try_get, error
from ..logger import debug_bot, error_bot

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: parse_message"
    message: Message = try_get(update, "message")
    if not message:
        error_message = f"{log_name}: No message data"
        error_bot.log(log_name, error_message)
        return error(error_message, data=update.to_json())
    debug_bot.log(f"{log_name} parse message success: message{message}")
    return success("Parse message success", data=message)


def parse_message_data(message: Message) -> Dict:
    log_name: str = f"{__name__}: parse_message_data"
    message_text = try_get(message, "text")
    message_date = try_get(message, "date")
    debug_bot.log(f"{log_name}: text={message_text}, date={message_date}")
    return message_text, message_date

def parse_message_data_keys(message, keys):
    extra_data = dict()
    for key in keys:
    if kwargs:
        for kwarg in kwargs:
            extra_data[kwarg] = try_get(message, kwarg)

def parse_chat(message: Message, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: parse_chat"
    chat: Chat = try_get(message, "chat")
    if not chat:
        error_message = f"{log_name}: No chat data"
        error_bot.log(log_name, error_message)
        return error(error_message, data=message.to_json())
    debug_bot.log(f"{log_name}: chat={chat}")
    return success("Parse chat success", data=chat)


def parse_chat_data(chat: Chat) -> Dict:
    log_name: str = f"{__name__}: parse_chat_data"
    chat_id: int = try_get(chat, "id")
    chat_title: str = try_get(chat, "title")
    chat_type: str = try_get(chat, "type")
    debug_bot.log(f"{log_name}: chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")
    return chat_id, chat_title, chat_type


def parse_user(message: Message, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: parse_user"
    user: User = try_get(message, "from_user")
    if not user:
        error_message = f"{log_name}: No user data"
        error_bot.log(log_name, error_message)
        return error(error_message, data=message.to_json())
    debug_bot.log(f"{log_name}: {user}")
    return dict(status="success", data=user)


def parse_user_data(user: User) -> Dict:
    log_name: str = f"{__name__}: parse_user_data"
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    debug_bot.log(f"{log_name}: user_id={user_id} username={username}")
    return username, user_id


async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: get_chat_admins"
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    chat_admin_data = dict(ids=admin_ids, usernames=admin_usernames)
    debug_bot.log(f"{log_name}: chat_admin_data={chat_admin_data}")
    return chat_admin_data


async def squawk_error(error_message: str, context: ContextTypes.DEFAULT_TYPE) -> Message:
    log_name: str = f"{__name__}: squawk_error"
    error_bot.log(f"{log_name}: {error_message}")
    return await context.bot.send_message(chat_id=THE_CREATOR, text=error_message)


def calculate_tokens(history: List) -> int:
    total = 0
    for data in history:
        content = try_get(data, "content")
        if not content:
            continue
        total += len(encoding.encode(content, allowed_special="all"))
    return total
