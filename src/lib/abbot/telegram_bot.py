# core
from datetime import datetime
import json
from io import open
from os.path import abspath
from typing import Dict, List, Optional, Tuple
import IPython

# packages
from telegram import ChatMember, Update, Message, Chat, User
from telegram.constants import MessageEntityType
from telegram.ext import (
    ContextTypes,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, REPLY

MENTION = MessageEntityType.MENTION
CHAT_CREATED = StatusUpdate.CHAT_CREATED
GROUPS = ChatType.GROUPS
PRIVATE = ChatType.PRIVATE
ENTITY_REPLY = Entity(REPLY)

# local
from constants import HELP_MENU, INTRODUCTION, THE_CREATOR
from ..logger import bot_debug, bot_error
from ..utils import error, sender_is_group_admin, success, try_get, successful
from ..db.utils import successful_insert_one, successful_update_one
from ..db.mongo import GroupConfig, TelegramDocument, TelegramGroupDocument, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.exceptions.exception import try_except
from ..abbot.config import BOT_CORE_SYSTEM, BOT_NAME, BOT_TELEGRAM_HANDLE
from ..abbot.utils import (
    parse_chat,
    parse_chat_data,
    parse_message,
    parse_message_data,
    parse_user,
    parse_user_data,
    squawk_error,
)
from ..admin.admin_service import AdminService

FULL_TELEGRAM_HANDLE = f"@{BOT_TELEGRAM_HANDLE}"

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")

admin = AdminService(THE_CREATOR, THE_CREATOR)
admin.status = "running"


async def parse_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Message, Chat, User]:
    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response) or not message:
        return await squawk_error(message, context)

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response) or not chat:
        error_message = try_get(message, "data")
        return await squawk_error(error_message, context)

    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response) or not user:
        return await squawk_error(user, context)

    return (message, chat, user)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "handle_text_message:"
    if not update or not context:
        return bot_error.log(f"{fn} No update or context")

    bot_debug.log(f"{fn} Update={update}")
    bot_debug.log(f"{fn} Context={context}")

    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        return await squawk_error(message, context)

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(message, "data")
        return await squawk_error(error_message, context)
    chat_data: Dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_type: str = try_get(chat_data, "type")
    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    chat_title: str = try_get(chat_data, "title", default="private" if is_private_chat else None)
    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        return await squawk_error(user, context)
    user_data: Dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")

    # log all data for debugging
    abbot_context = "group"

    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")

    abbot_message = dict(role="user", content=message_text)
    if is_group_chat and "test" not in BOT_TELEGRAM_HANDLE:
        bot_debug.log(f"{fn} is_group_chat={is_group_chat}")
        bot_debug.log(f"{fn} test not in BOT_TELEGRAM_HANDLE={BOT_TELEGRAM_HANDLE}")
        message_dump = json.dumps(
            {"message": {**message_data}, "chat": {**chat_data}, "user": {**user_data}, "abbot": abbot_message}
        )
        bot_debug.log(f"{fn} message_dump={message_dump}")
        raw_messages_jsonl = open(RAW_MESSAGE_JL_FILE, "a")
        raw_messages_jsonl.write(message_dump)
        raw_messages_jsonl.write("\n")
        raw_messages_jsonl.close()
    else:
        abbot_context = "private"
        bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    bot_debug.log(f"{fn} abbot_context={abbot_context}")

    abbot = Abbot(chat_id)

    # not_introduced: bool = abbot.is_forgotten()
    # if not_introduced:
    #     debug. log(f"{fn} Abbot not introduced!")
    #     abbot.introduce()
    #     introduced = abbot.is_introduced()
    #     debug. log(f"introduced={introduced}")
    #     abbots.update_abbots(chat_id, abbot)
    #     return await message.reply_text(
    #         "Thank you for talking to Abbot (@atl_bitlab_bot), a bitcoiner bot for bitcoin communities, by the Atlanta Bitcoin community!\n\n"
    #         "Abbot is meant to provide education to local bitcoin communities and help community organizers with various tasks.\n\n"
    #         "To start Abbot in a group chat, have a channel admin run /start\n"
    #         "To start Abbot in a DM, simply run /start.\n\n"
    #         "By running /start, you agree to our Terms & policies: https://atlbitlab.com/abbot/policies.\n\n"
    #         "If you have multiple bots in one channel, you may need to run /start@atl_bitlab_bot to avoid bot confusion!\n\n"
    #         "If you have questions, concerns, feature requests or find bugs, please contact @nonni_io or @ATLBitLab on Telegram."
    #     )

    # not_started: bool = abbot.is_stopped()
    # if not_started:
    #     debug. log(f"{fn} Abbot introduced!")
    #     debug. log(f"{fn} Abbot not started!")
    #     return

    message_reply = try_get(message, "reply_to_message")
    message_reply_text = try_get(message_reply, "text")
    message_reply_from = try_get(message_reply, "from")
    if is_private_chat:
        abbot.update_chat_history(abbot_message)
        bot_debug.log(f"{fn} is private, not group_in_name")
        answer = abbot.chat_history_completion()
    else:
        chat_history_len: int = abbot.chat_history_len
        is_unleashed, count = abbot.is_unleashed()
        bot_debug.log(f"{fn} group_in_name: name={abbot.name}")
        if handle not in message_text and handle not in message_reply_text:
            bot_debug.log(f"{fn} handle not in message_text or message_reply_text")
            return
        if not replied_to_abbot:
            bot_debug.log(f"{fn} not replied_to_abbot!")
            return
        if not is_unleashed or not count:
            bot_debug.log(f"{fn} not is_unleashed or not count")
            return
        if chat_history_len % count != 0:
            bot_debug.log(f"{fn} chat_history_len % count != 0!")
            return
        bot_debug.log(f"{fn} All checks passed!")
        answer = abbot.chat_history_completion()
    # if not answer:
    #     await context.bot.send_message(
    #         chat_id=THE_CREATOR,
    #         text=f"{abbot.name} completion failed ⛔️: abbot={abbot} answer={answer}",
    #     )
    # i = 0
    # while not answer and i < 5:
    #     abbot.sleep(10)
    #     answer = abbot.chat_history_completion()
    #     debug. log(f"{fn} answer={answer}")
    #     if answer:
    #         continue
    #     i += 1
    # if not answer:
    #     return await context.bot.send_message(
    #         chat_id=user_id, text="Sorry, I seem to have bugged out bug 🐜 please contact @nonni_io for help."
    #     )
    return await message.reply_text(answer)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "help:"
    message: Message = parse_message(update)
    chat: Chat = parse_chat(update, message)
    user: User = parse_user(message)
    user_data: Dict = parse_user_data(user)
    message_data: Dict = parse_message_data(message)
    chat_data: Dict = parse_chat_data(chat)
    # log all data for debugging
    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")
    await message.reply_text(HELP_MENU)


async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "unleash:"
    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        data = message
        return await squawk_error(data, context)
    message_data: Dict = parse_message_data(message)

    response: Dict = parse_chat(update, message)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        data = chat
        return await squawk_error(data, context)
    chat_data: Dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_title: str = try_get(chat_data, "title")
    chat_type: str = try_get(chat_data, "type")

    response: Dict = parse_user(message)
    user: User = try_get(response, "data")
    if not successful(response):
        data = user
        return await squawk_error(data, context)
    user_data: Dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")

    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    # log all data for debugging
    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")

    abbot_context = "group"
    if is_private_chat:
        abbot_context = "private"
    elif is_group_chat:
        is_admin = await sender_is_group_admin(context, chat_id, user_id)
        if not is_admin:
            return await message.reply_text(f"Forbidden: Admin only. {username} is not an admin of {chat_title}.")

    bot_debug.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = Abbot(chat_id)
    if abbot.is_stopped():
        return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    unleashed, count = abbot.is_unleashed()
    if unleashed:
        return await message.reply_text(f"I'm already unleashed for {chat_title}! To leash me, please run /leash!")

    abbot.unleash()
    unleashed, count = abbot.is_unleashed()
    bot_debug.log(f"{fn} {abbot} unleashed={unleashed}")
    return await message.reply_text(
        f"I have been unleashed! I will now respond every {count} messages until"
        "you run /leash or /unleash <insert_new_number> (e.g. /unleash 10)"
    )


async def leash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "leash:"
    message: Message = parse_message(update)
    message_data: Dict = parse_message_data(message)

    chat: Chat = parse_chat(update, message)
    chat_data: Dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_title: str = try_get(chat_data, "title")
    chat_type: str = try_get(chat_data, "type")

    user: User = parse_user(message)
    user_data: Dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")

    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    abbot_context = "group"
    # log all data for debugging
    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")
    if is_private_chat:
        abbot_context = "private"
    elif is_group_chat:
        is_admin = await sender_is_group_admin(context, chat_id, user_id)
        if not is_admin:
            return await message.reply_text(f"Forbidden: Admin only. {username} is not an admin of {chat_title}.")
    bot_debug.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = Abbot(chat_id)
    if abbot.is_stopped():
        return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    leashed, count = abbot.is_leashed()
    if leashed:
        return await message.reply_text(f"I'm already leashed for {chat_title}! To unleash me, please run /leash!")

    abbot.leash()
    leashed, count = abbot.is_leashed()
    bot_debug.log(f"{fn} leashed={leashed}")
    return await message.reply_text(
        f"I have been leashed! To unleash me again, run /unleash or /unleash <insert_new_number> (e.g. /unleash 10)"
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "rules:"
    message: Message = try_get(update, "message")
    chat: Chat = try_get(message, "chat")
    user: User = try_get(message, "from_user")
    if not message or not chat or not user:
        bot_error.log(f"{fn} missing message: {message}")
        bot_error.log(f"{fn} missing chat: {chat}")
        bot_error.log(f"{fn} missing user: {user}")
        return
    bot_debug.log(f"{fn} message={message}")
    bot_debug.log(f"{fn} chat={chat}")
    bot_debug.log(f"{fn} user={user}")
    chat_id: int = try_get(chat, "id")
    user_id: int = try_get(user, "id")
    username: int = try_get(user, "username")
    chat_type: str = try_get(chat, "type")
    if not chat_id or not chat_type or not user_id:
        bot_error.log(f"{fn} missing chat id: {chat_id}")
        bot_error.log(f"{fn} missing chat type: {chat_type}")
        bot_error.log(f"{fn} missing user id: {user_id}")
        return
    bot_debug.log(f"{fn} chat_id={chat_id}")
    bot_debug.log(f"{fn} chat_type={chat_type}")
    bot_debug.log(f"{fn} user_id={user_id}")
    bot_debug.log(f"{fn} executed by username={username} user_id={user_id}")
    await message.reply_text(
        "Hey! The name's Abbot but you can think of me as your go-to guide for all things Bitcoin. AKA the virtual Bitcoin whisperer. 😉\n\n"
        "Here's the lowdown on how to get my attention: \n\n"
        "1. Slap an @atl_bitlab_bot before your message in the group chat - I'll come running to answer. \n"
        "2. Feel more comfortable replying directly to my messages? Go ahead! I'm all ears.. err.. code. \n"
        "3. Fancy a one-on-one chat? Slide into my DMs. \n\n"
        "Now, enough with the rules! Let's dive into the world of Bitcoin together! \n\n"
        "Ready. Set. Stack Sats! 🚀"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "start:"
    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        return squawk_error(message, context)

    message_data: Dict = parse_message_data(message)
    message_text: str = try_get(message_data, "text")
    message_date: str = try_get(message_data, "date")

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(message, "data")
        return squawk_error(error_message, context)
    chat_data: Dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_type: str = try_get(chat_data, "type")
    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    chat_title: str = try_get(chat_data, "title", default="private" if is_private_chat else None)

    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        return await squawk_error(user, context)
    user_data: Dict = parse_user_data(user)

    # log all data for debugging
    abbot_context = "group"
    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")

    if is_group_chat:
        is_admin = await sender_is_group_admin(context)
        if not is_admin:
            return await message.reply_text("Forbidden: Admin only!")
    else:
        abbot_context = "private"
        bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    bot_debug.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = Abbot(chat_id)
    if abbot.is_started():
        return await message.reply_text("Abbot already started!")
    abbot.start()
    started = abbot.is_started()
    bot_debug.log(f"{fn} abbot={abbot.to_dict()} started={started}")
    await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while we unplug {BOT_NAME} from the Matrix")
    response = abbot.chat_completion()
    if not response:
        return await context.bot.send_message(
            chat_id=THE_CREATOR,
            text=f"chat_title={chat_title} chat_id={chat_id}",
        )
    await message.reply_text(response)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "stop:"
    message: Message = try_get(update, "message")
    chat: Chat = try_get(message, "chat")
    user: User = try_get(message, "from_user")
    if not message or not chat or not user:
        bot_error.log(f"{fn} missing message: {message}")
        bot_error.log(f"{fn} missing chat: {chat}")
        bot_error.log(f"{fn} missing user: {user}")
        return
    bot_debug.log(f"{fn} message={message}")
    bot_debug.log(f"{fn} chat={chat}")
    bot_debug.log(f"{fn} user={user}")
    chat_id: int = try_get(chat, "id")
    user_id: int = try_get(user, "id")
    chat_type: str = try_get(chat, "type")
    chat_title: str = try_get(chat, "title")
    if not chat_id or not chat_type or not user_id:
        bot_error.log(f"{fn} missing chat id: {chat_id}")
        bot_error.log(f"{fn} missing chat type: {chat_type}")
        bot_error.log(f"{fn} missing user id: {user_id}")
        return
    bot_debug.log(f"{fn} chat_id={chat_id}")
    bot_debug.log(f"{fn} chat_type={chat_type}")
    bot_debug.log(f"{fn} user_id={user_id}")
    abbot_context = "group"
    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    if is_group_chat:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in admins]
        if user_id not in admin_ids:
            return await update.message.reply_text("Forbidden: Admin only!")
    else:
        abbot_context = "private"
        bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    bot_debug.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = Abbot(chat_id)
    if not abbot.started:
        await message.reply_text("Abbot isn't started yet! Have an admin run /start")
        return await context.bot.send_message(chat_id=THE_CREATOR, text=f"chat_title={chat_title} chat_id={chat_id}")
    started = abbot.stop()
    if not started:
        raise Exception(f"Not started! started={started}")
    await message.reply_text("Thanks for using Abbot! To restart, use the /start command at any time.")


async def admin_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "_admin_plugin:"
    chat_id: int = try_get(update, "message", "chat", "id")
    user_id: int = try_get(update, "message", "from_user", "id")
    if user_id != THE_CREATOR:
        return
    admin: AdminService = AdminService(user_id, chat_id)
    admin.stop_service()


async def admin_unplug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_unplug:"
    chat_id: int = try_get(update, "message", "chat", "id")
    user_id: int = try_get(update, "message", "from_user", "id")
    admin: AdminService = AdminService(user_id, chat_id)
    admin.start_service()


async def admin_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_kill:"
    message: Message = try_get(update, "message")
    chat: Chat = try_get(message, "chat")
    chat_id: int = try_get(chat, "id")
    user: User = try_get(message, "from_user")
    user_id: int = try_get(user, "id")
    if user_id != THE_CREATOR:
        return
    admin: AdminService = AdminService(user_id, chat_id)
    admin.kill_service()


async def admin_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_nap:"
    message: Message = try_get(update, "message")
    chat: Chat = try_get(message, "chat")
    chat_id: int = try_get(chat, "id")
    user: User = try_get(message, "from_user")
    user_id: int = try_get(user, "id")
    if user_id != THE_CREATOR:
        return
    admin: AdminService = AdminService(user_id, chat_id)
    admin.sleep_service()


async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_status:"
    message: Message = try_get(update, "message")
    chat: Chat = try_get(message, "chat")
    chat_id: int = try_get(chat, "id")
    user: User = try_get(message, "from_user")
    user_id: int = try_get(user, "id")
    if user_id != THE_CREATOR:
        return
    abbot: Abbot = Abbot(chat_id)
    status_data = json.dumps(abbot.get_config(), indent=4)
    bot_debug.log(f"statuses => {abbot} status_data={status_data}")
    await message.reply_text(status_data)


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_dm")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    mongo_dm_filter = {"id": chat.id}
    chat_type: ChatType = chat.type
    if chat_type != "private":
        bot_error.log(__name__, f"chat_type not private")
        return await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"chat_id={chat.id} chat_type={chat_type} chat_title={chat.title}"
        )
    tg_doc: TelegramDocument = TelegramDocument(message=message)
    tg_doc_dict = tg_doc.to_dict()
    bot_debug.log(__name__, f"telegram_bot => handle_dm => tg_doc={tg_doc}")
    bot_debug.log(__name__, f"telegram_bot => handle_dm => tg_doc_dict={tg_doc_dict}")

    tg_dm = mongo_abbot.find_one_dm_and_update(
        mongo_dm_filter,
        {"$push": {"messages": message.to_dict(), "history": {"role": "user", "content": message.text}}},
    )
    if not tg_dm:
        insert = mongo_abbot.insert_one_dm(tg_doc_dict)
        if not successful_insert_one(insert):
            bot_error.log(__name__, f"telegram_bot => handle_dm => insert failed={insert}")
        bot_debug.log(__name__, f"telegram_bot => handle_dm => insert={insert}")
        tg_dm = mongo_abbot.find_one_dm(mongo_dm_filter)
    bot_debug.log(__name__, f"telegram_bot => handle_dm => tg_dm={tg_dm}")
    abbot = Abbot(chat.id, "dm", tg_dm)
    # bot_debug.log(__name__, f"telegram_bot => handle_dm => abbot={abbot.to_dict()}")
    abbot.update_history({"role": "user", "content": message.text})
    bot_debug.log(__name__, f"chat_id={chat.id}, {user.username} dms with Abbot")
    answer = abbot.chat_completion()
    return await message.reply_text(answer)


async def handle_group_chat_update(message: Message, chat: Chat, user: User):
    bot_debug.log("group_doc_exists", group_doc_exists)
    tg_doc_dict = tg_doc.to_dict()
    bot_debug.log("tg_doc_dict", tg_doc_dict)
    channel = mongo_abbot.find_one_channel({"id": chat.id})
    bot_debug.log("channel", channel)
    if not channel:
        mongo_abbot.insert_one_dm(TelegramDocument(message).to_dict())
    abbot = Abbot(chat.id, "channel")
    abbot.update_history({"role": "user", "content": message.text})
    bot_debug.log(f"{__name__} chat_id={chat.id}, {user.username} mentioned Abbot")
    answer = abbot.chat_completion()
    return await message.reply_text(answer)


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    group_doc_exists = mongo_abbot.find_one_channel({"id": chat.id})
    if not group_doc_exists:
        bot_debug.log(f"handle_group_mention => not group_doc_exists={not group_doc_exists}")
        return
    return await handle_group_chat_update(message, chat, user)


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    from_user: Optional[User] = try_get(message, "reply_to_message", "from_user")
    if from_user.is_bot and from_user.username == BOT_TELEGRAM_HANDLE:
        # TODO: add to db, send to gpt, reply
        pass


async def handle_insert_group_doc(message: Message, chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    new_group_doc: TelegramGroupDocument = TelegramGroupDocument(message, admins)
    bot_debug.log(f"handle_insert_group_doc => new_group_doc={new_group_doc}")
    new_group_insert = mongo_abbot.insert_one_channel(
        {
            "title": chat.title,
            "id": chat.id,
            "created_at": datetime.now(),
            "type": chat.type,
            "admins": list(admins),
            "balance": 50000,
            "message": [],
            "history": [
                {"role": "system", "content": BOT_CORE_SYSTEM},
                {"role": "assistant", "content": INTRODUCTION},
            ],
            "config": {"started": True, "introduced": True, "unleashed": False, "count": None},
        }
    )
    if not successful_insert_one(new_group_insert):
        bot_error.log(__name__, f"handle_added_to_chat => insert failed={new_group_insert}")
        return error("Insert new group doc success", data=new_group_insert)
    return success("New group doc inserted", data=new_group_doc)


async def handle_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_added_to_chat")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    bot_debug.log(__name__, f"update_data={update_data}")
    admins: Tuple[ChatMember] = await chat.get_administrators()
    abbot_added = False
    for member in message.new_chat_members:
        if member.username == BOT_TELEGRAM_HANDLE:
            abbot_added = True
            break
    if not abbot_added:
        bot_debug.log(f"handle_added_to_chat => abbot_added={abbot_added}")
        return
    group_doc_exists = mongo_abbot.find_one_channel({"id": chat.id})
    if group_doc_exists:
        bot_debug.log(f"handle_added_to_chat => group_doc_exists={group_doc_exists}")
        return
    response: Dict = await handle_insert_group_doc(message, chat, admins)
    if not successful(response):
        admin_list: List = list(admins)
        bot_error.log(__name__, f"Insert new group doc fail")
        return await context.bot.send_message(chat_id=try_get(admin_list, 0), text=response.get("message"))
    return await message.reply_text(chat_id=chat.id, text=INTRODUCTION)


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        bot_debug.log(f"Telegram abbot initializing: name={BOT_NAME} handle={FULL_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        bot_debug.log(f"Telegram abbot initialized")

        # Add command handlers
        telegram_bot.add_handlers(
            handlers=[
                CommandHandler("unplug", admin_unplug),
                CommandHandler("plugin", admin_plugin),
                CommandHandler("kill", admin_kill),
                CommandHandler("nap", admin_nap),
                CommandHandler("status", admin_status),
                CommandHandler("help", help),
                CommandHandler("rules", rules),
                CommandHandler("start", start),
                CommandHandler("stop", stop),
                CommandHandler("unleash", unleash),
                CommandHandler("leash", leash),
            ]
        )
        # Add message handlers
        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(PRIVATE, handle_dm),
                MessageHandler(GROUPS & CHAT_CREATED, handle_added_to_chat),
                MessageHandler(GROUPS & Entity(MENTION) & Regex(FULL_TELEGRAM_HANDLE), handle_group_mention),
                MessageHandler(GROUPS & Entity(REPLY), handle_group_reply),
            ]
        )

        self.telegram_bot = telegram_bot

    def run(self):
        bot_debug.log(f"Telegram abbot polling")
        self.telegram_bot.run_polling()
