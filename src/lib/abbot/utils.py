import tiktoken

from typing import Dict, List
from random import randrange
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from constants import OPENAI_MODEL, THE_CREATOR

from ..utils import try_get
from ..db.mongo import MongoAbbot, TelegramGroup
from ..abbot.config import BOT_RESPONSES
from ..logger import bot_debug, bot_error

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    chat_admin_data = dict(ids=admin_ids, usernames=admin_usernames)
    bot_debug.log(f"{__name__} chat_admin_data={chat_admin_data}")
    return chat_admin_data


def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    message: Message = try_get(update, "message")
    if not message:
        error_message = f"{__name__} No message: update={update.to_json()} context={context}"
        return dict(status="error", data=error_message)
    bot_debug.log(f"{__name__} message={message}")
    return dict(status="success", data=message)


def parse_message_data(message: Message) -> Dict:
    message_text = try_get(message, "text")
    message_date = try_get(message, "date")
    message_data: dict = dict(status="success", text=message_text, date=message_date)
    bot_debug.log(f"{__name__} message_data={message_data}")
    return message_data


def parse_chat(message: Message, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    chat: Chat = try_get(message, "chat")
    if not chat:
        error_message = f"{__name__} No chat: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    bot_debug.log(f"{__name__} chat={chat}")
    return dict(status="success", data=chat)


def parse_chat_data(chat: Chat) -> Dict:
    chat_id: int = try_get(chat, "id")
    chat_title: str = try_get(chat, "title")
    chat_type: str = try_get(chat, "type")
    chat_data = dict(id=chat_id, title=chat_title, type=chat_type)
    bot_debug.log(f"{__name__} chat_data={chat_data}")
    return chat_data


def parse_user(message: Message, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    user: User = try_get(message, "from_user")
    if not user:
        error_message = f"{__name__} No user: update={message.to_json()} context={context}"
        return dict(status="error", data=error_message)
    bot_debug.log(f"{__name__} {user}")
    return dict(status="success", data=user)


def parse_user_data(user: User) -> Dict:
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    user_data = dict(user_id=user_id, username=username)
    bot_debug.log(f"{__name__} {user_data}")
    return user_data


async def squawk_error(error_message: str, context: ContextTypes.DEFAULT_TYPE) -> Message:
    bot_error.log(f"{__name__} {error_message}")
    return await context.bot.send_message(chat_id=THE_CREATOR, text=error_message)


def get_bot_response(response_type: str, index: int = None) -> str:
    response_list = try_get(BOT_RESPONSES, response_type)
    index = randrange(len(response_list)) if not index else index
    return try_get(response_list, index)


def calculate_tokens(history: List) -> int:
    total = 0
    for data in history:
        total += len(encoding.encode(try_get(data, "content"), allowed_special="all"))
    return total


def get_current_group_sats_balance(chat_id: int):
    channel: TelegramGroup = MongoAbbot.find_one_channel({"id": chat_id})
    return try_get(channel, "balance")
