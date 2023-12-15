import tiktoken

from typing import Dict, List
from random import randrange
from telegram.ext import ContextTypes
from telegram import Message, Update, Chat, User

from constants import OPENAI_MODEL, THE_CREATOR

from ..utils import success, successful, try_get, error
from ..logger import debug_bot, error_bot

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


async def parse_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: parse_update_data"

    response: Dict = parse_message(update)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response}\nerror_message={error_message}\nerror_data={error_data}")
        await squawk_error(error_message, context)
        return error(f"Parse message from update failed", data=error_message)
    message: Message = try_get(response, "data")

    response: Dict = parse_chat(message, update)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response}\nerror_message={error_message}\nerror_data={error_data}")
        await squawk_error(error_message, context)
        return error(f"Failed to parse chat from update: {error_message}", data=error_data)
    chat: Chat = try_get(response, "data")

    response: Dict = parse_user(message)
    if not successful(response):
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response}\nerror_message={error_message}\nerror_data={error_data}")
        await squawk_error(user, context)
        return error(f"Failed to parse user from update: {error_message}", data=error_data)
    user: User = try_get(response, "data")

    return success("Parse update success", data=dict(message=message, chat=chat, user=user))


def parse_message(update: Update) -> Dict:
    log_name: str = f"{__name__}: parse_message"
    message: Message = try_get(update, "message") or try_get(update, "effective_message")
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
        extra_data[key] = try_get(message, key)
    return extra_data


def parse_chat(message: Message, update: Update) -> Dict:
    log_name: str = f"{__name__}: parse_chat"
    chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
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


def parse_user(message: Message) -> Dict:
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
    return user_id, username


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


"""
def update_telegram_group_doc(existing: Dict, update: Dict) -> Dict:
    log_name: str = f"{__name__}: update_telegram_group_doc"
    chat_id = try_get(existing, "id")
    doc_filter = {"id": chat_id}
    updates = {}
    for key, value in update.items():
        if existing.get(key) != value:
            updates[key] = value
    group: TelegramGroup = mongo_abbot.update_one_group(doc_filter, {"$set": updates})
    if not successful_update_one(group):
        error_bot.log(log_name, f"Failed to update group doc")
        return error("Failed to update group doc", data=group)
    group: TelegramGroup = mongo_abbot.find_one_group(doc_filter)
    if not group:
        error_bot.log(log_name, f"")
        return error("Failed to update group doc", data=group)
    object_id = try_get(group, "_id")
    if object_id:
        group = {**group, "_id": str(object_id)}
    created_at = try_get(group, "created_at")
    if created_at and type(created_at) == datetime:
        group = {**group, "created_at": json_util.dumps(created_at)}
    return success("Success update group doc", data=group)
def create_telegram_group_doc(message: Message, chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    log_name: str = f"{__name__}: create_telegram_group_doc: "
    debug_bot.log(log_name, f"creating doc for chat.id={chat.id}")
    return {
        "title": chat.title,
        "id": chat.id,
        "created_at": datetime.now().isoformat(),
        "type": chat.type,
        "admins": list(admins),
        "balance": 50000,
        "messages": [message.to_dict()],
        "history": BOT_SYSTEM_OBJECT_GROUPS,
        "config": {"started": False, "introduced": False, "unleashed": False, "count": None},
    }
def handle_insert_group(message: Message, chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    log_name: str = f"{__name__}: handle_insert_group"
    group_doc: TelegramGroup = create_telegram_group_doc(message, chat, admins)
    insert: InsertOneResult = mongo_abbot.insert_one_group(group_doc)
    if not successful_insert_one(insert):
        error_bot.log(log_name, f"insert={insert}")
        return error(f"Insert new group doc failed", data=insert)
    group: TelegramGroup = mongo_abbot.find_one_group({"id": chat.id})
    return success("New group doc inserted", data=group)
"""
