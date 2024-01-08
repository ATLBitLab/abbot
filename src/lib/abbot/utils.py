from typing import Any, Dict, List, Optional

import tiktoken
from json import dumps
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from constants import ABBOT_SQUAWKS, OPENAI_MODEL, THE_ARCHITECT_HANDLE, THE_ARCHITECT_ID

from ..utils import success, successful, try_get, error
from ..logger import debug_bot, error_bot

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)

FILE_NAME = __name__


def parse_message(update: Update) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_message"
    message_update: Optional[Message] = try_get(update, "message")
    edited_message: Optional[Message] = try_get(update, "edited_message")
    effective_message: Optional[Message] = try_get(update, "_effective_message")
    message: Optional[Message] = message_update or edited_message or effective_message
    if not message:
        error_message = f"{log_name}: No message, edited_message or effective_message"
        error_bot.log(log_name, error_message)
        update_dict = update.to_json()
        error_bot.log(log_name, f"update={dumps(update_dict, indent=4)}")
        return error(error_message, data=update_dict)
    debug_bot.log(f"{log_name} message{message}")
    return success(data=message)


def parse_message_data(message: Message) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_message_data"
    message_text = try_get(message, "text")
    message_date = try_get(message, "date")
    debug_bot.log(f"{log_name}: text={message_text}, date={message_date}")
    return message_text, message_date


def parse_message_data_keys(message, keys):
    extra_data = dict()
    for key in keys:
        extra_data[key] = try_get(message, key)
    return extra_data


def parse_chat(message: Message, update: Update) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_chat"
    chat_update: Chat = try_get(message, "chat")
    effective_chat: Optional[Chat] = try_get(update, "_effective_chat")
    chat: Optional[Chat] = chat_update or effective_chat
    if not chat:
        error_message = f"{log_name}: No chat or effective_chat data"
        error_bot.log(log_name, error_message)
        return error(error_message, data=message.to_json())
    debug_bot.log(f"{log_name}: chat={chat}")
    return success(data=chat)


def parse_group_chat_data(chat: Chat) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_group_chat_data"
    chat_id: int = try_get(chat, "id")
    chat_title: str = try_get(chat, "title")
    chat_type: str = try_get(chat, "type")
    debug_bot.log(f"{log_name}: chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")
    return chat_id, chat_title, chat_type


def parse_dm_chat_data(chat: Chat) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_dm_chat_data"
    dm_user_id: int = try_get(chat, "id")
    dm_username: str = try_get(chat, "username")
    dm_first_name: str = try_get(chat, "first_name")
    debug_bot.log(f"{log_name}: dm_user_id={dm_user_id} dm_username={dm_username} dm_first_name={dm_first_name}")
    return dm_user_id, dm_username, dm_first_name


def parse_user(message: Message, update: Update) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_user"
    user_update: Optional[User] = try_get(message, "from_user")
    effective_user: Optional[User] = try_get(update, "_effective_user")
    user: Optional[User] = user_update or effective_user
    if not user:
        error_message = f"{log_name}: No user or effective_user data"
        error_bot.log(log_name, error_message)
        return error(error_message, data=message.to_json())
    debug_bot.log(f"{log_name}: {user}")
    return success(data=user)


def parse_user_data(user: User) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_user_data"
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    first_name: int = try_get(user, "first_name")

    debug_bot.log(f"{log_name}: user_id={user_id} username={username} first_name={first_name}")
    return user_id, username, first_name


async def parse_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{FILE_NAME}: parse_update_data"

    response: Dict = parse_message(update)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        log_msg = f"response={response}\nerror_message={error_message}\nerror_data={error_data}"
        error_bot.log(log_name, log_msg)
        await bot_squawk(error_message, context)
        return error(f"Parse message from update failed", data=error_message)
    message: Message = try_get(response, "data")

    response: Dict = parse_chat(message, update)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response}\nerror_message={error_message}\nerror_data={error_data}")
        await bot_squawk(error_message, context)
        return error(f"Failed to parse chat from update: {error_message}", data=error_data)
    chat: Chat = try_get(response, "data")

    response: Dict = parse_user(message, update)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response}\nerror_message={error_message}\nerror_data={error_data}")
        await bot_squawk(user, context)
        return error(f"Failed to parse user from update: {error_message}", data=error_data)
    user: User = try_get(response, "data")

    return success("Parse update success", data=dict(message=message, chat=chat, user=user))


async def get_chat_admins(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{FILE_NAME}: get_chat_admins"
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [try_get(admin, "user", "id") for admin in chat_admins]
    admin_usernames = [try_get(admin, "user", "username") for admin in chat_admins]
    chat_admin_data = dict(ids=admin_ids, usernames=admin_usernames)
    debug_bot.log(f"{log_name}: chat_admin_data={chat_admin_data}")
    return chat_admin_data


async def bot_squawk_architect(error_message: str, context: ContextTypes.DEFAULT_TYPE) -> Message:
    log_name: str = f"{FILE_NAME}: bot_squawk"
    error_bot.log(f"{log_name}: {error_message}")
    return await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=error_message)


async def bot_squawk(location: str, squawk: str, context: ContextTypes.DEFAULT_TYPE) -> Message:
    log_name: str = f"{FILE_NAME}: bot_squawk"
    error_bot.log(f"{log_name}: {squawk}")
    final_squawk = f"{THE_ARCHITECT_HANDLE} Abbot Error\n\nLocation\n{location}\n\nException\n{squawk}"
    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=final_squawk)


def calculate_tokens(history: List) -> int:
    total = 0
    for data in history:
        content = try_get(data, "content")
        if not content:
            continue
        total += len(encoding.encode(content, allowed_special="all"))
    return total


def to_int(x: Any) -> int:
    try:
        return int(x)
    except ValueError:
        return None
