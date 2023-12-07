# core
import json
import uuid
from io import open
from os.path import abspath
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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

from lib.payments import Strike, init_payment_processor

MENTION = MessageEntityType.MENTION
CHAT_CREATED = StatusUpdate.CHAT_CREATED
GROUPS = ChatType.GROUPS
PRIVATE = ChatType.PRIVATE
ENTITY_REPLY = Entity(REPLY)

# local
from constants import HELP_MENU, INTRODUCTION, THE_CREATOR
from ..logger import bot_debug, bot_error
from ..utils import error, qr_code, sender_is_group_admin, success, try_get, successful
from ..db.utils import successful_insert_one, successful_update_one
from ..db.mongo import GroupConfig, TelegramDM, TelegramGroup, mongo_abbot
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


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, _ = update_data
    await message.reply_text(HELP_MENU)


async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # if abbot.is_stopped():
    #     return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    # unleashed, count = abbot.is_unleashed()
    # if unleashed:
    #     return await message.reply_text(f"I'm already unleashed for {chat_title}! To leash me, please run /leash!")

    # abbot.unleash()
    # unleashed, count = abbot.is_unleashed()
    # bot_debug.log(f"{fn} {abbot} unleashed={unleashed}")
    # return await message.reply_text(
    #     f"I have been unleashed! I will now respond every {count} messages until"
    #     "you run /leash or /unleash <insert_new_number> (e.g. /unleash 10)"
    # )


async def leash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # abbot: Abbot = Abbot(chat_id)
    # if abbot.is_stopped():
    #     return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    # leashed, count = abbot.is_leashed()
    # if leashed:
    #     return await message.reply_text(f"I'm already leashed for {chat_title}! To unleash me, please run /leash!")
    # abbot.leash()
    # leashed, count = abbot.is_leashed()
    # bot_debug.log(f"{fn} leashed={leashed}")
    # return await message.reply_text(
    #     f"I have been leashed! To unleash me again, run /unleash or /unleash <insert_new_number> (e.g. /unleash 10)"
    # )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, __annotations__ = update_data
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
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # if is_group_chat:
    #     is_admin = await sender_is_group_admin(context)
    #     if not is_admin:
    #         return await message.reply_text("Forbidden: Admin only!")
    # else:
    #     abbot_context = "private"
    #     bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    # bot_debug.log(f"{fn} abbot_context={abbot_context}")
    # abbot: Abbot = Abbot(chat_id)
    # if abbot.is_started():
    #     return await message.reply_text("Abbot already started!")
    # abbot.start()
    # started = abbot.is_started()
    # bot_debug.log(f"{fn} abbot={abbot.to_dict()} started={started}")
    # await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while we unplug {BOT_NAME} from the Matrix")
    # response = abbot.chat_completion()
    # if not response:
    #     return await context.bot.send_message(
    #         chat_id=THE_CREATOR,
    #         text=f"chat_title={chat_title} chat_id={chat_id}",
    #     )
    # await message.reply_text(response)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic    abbot_context = "group"
    # is_private_chat: bool = chat_type == "private"
    # is_group_chat: bool = not is_private_chat
    # if is_group_chat:
    #     admins = await context.bot.get_chat_administrators(chat_id)
    #     admin_ids = [admin.user.id for admin in admins]
    #     if user_id not in admin_ids:
    #         return await update.message.reply_text("Forbidden: Admin only!")
    # else:
    #     abbot_context = "private"
    #     bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    # bot_debug.log(f"{fn} abbot_context={abbot_context}")
    # abbot: Abbot = Abbot(chat_id)
    # if not abbot.started:
    #     await message.reply_text("Abbot isn't started yet! Have an admin run /start")
    #     return await context.bot.send_message(chat_id=THE_CREATOR, text=f"chat_title={chat_title} chat_id={chat_id}")
    # started = abbot.stop()
    # if not started:
    #     raise Exception(f"Not started! started={started}")
    # await message.reply_text("Thanks for using Abbot! To restart, use the /start command at any time.")


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


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    admins: Tuple[ChatMember] = await chat.get_administrators()
    new_history_entry = {"role": "user", "content": message.text}
    # TODO: calculate cost of tokens and deduct from balance
    channel = mongo_abbot.find_one_channel_and_update(
        {"id": chat.id}, {"$push": {"messages": message.to_dict(), "history": new_history_entry}}
    )
    abbot = Abbot(chat.id, "channel", channel.history)
    abbot.update_history_meta(message.text)
    bot_debug.log(f"{__name__} chat_id={chat.id}, {user.username} mentioned Abbot")
    answer = abbot.chat_completion()
    return await message.reply_text(answer)


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, _ = update_data
    from_user: Optional[User] = try_get(message, "reply_to_message", "from_user")
    if from_user.is_bot and from_user.username == BOT_TELEGRAM_HANDLE:
        return await handle_group_mention(update, context)


async def handle_insert_channel(chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    channel = mongo_abbot.insert_one_channel(
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
    if not successful_insert_one(channel):
        bot_error.log(__name__, f"handle_added_to_chat => insert failed={channel}")
        return error("Insert new group doc success", data=channel)
    return success("New group doc inserted", data=channel)


async def handle_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_added_to_chat")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, _ = update_data

    admins: Tuple[ChatMember] = await chat.get_administrators()
    abbot_added = False
    for member in message.new_chat_members:
        if member.username == BOT_TELEGRAM_HANDLE:
            abbot_added = True
            break
    if not abbot_added:
        bot_debug.log(f"handle_added_to_chat => abbot_added={abbot_added}")
        return

    channel = mongo_abbot.find_one_channel({"id": chat.id})
    if channel:
        bot_debug.log(f"handle_added_to_chat => channel={channel}")
        return

    response: Dict = await handle_insert_channel(chat, admins)
    if not successful(response):
        admin_list: List = list(admins)
        bot_error.log(__name__, f"Insert new channel fail")
        return await context.bot.send_message(chat_id=try_get(admin_list, 0), text=response.get("message"))

    return await message.reply_text(chat_id=chat.id, text=INTRODUCTION)


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_dm")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    dm: TelegramDM = mongo_abbot.find_one_dm({"chat": chat.id})
    if not dm:
        dm = mongo_abbot.insert_one_dm(
            {
                "id": chat.id,
                "username": message.from_user.username,
                "created_at": datetime.now(),
                "messages": [message.to_dict()],
                "history": [{"role": "system", "content": BOT_CORE_SYSTEM}, {"role": "user", "content": message.text}],
            }
        )
        if not successful_insert_one(dm):
            bot_error.log(__name__, f"telegram_bot => handle_dm => insert dm failed={dm}")
        bot_debug.log(__name__, f"telegram_bot => handle_dm => dm={dm}")
        dm = mongo_abbot.find_one_dm({"id": chat.id})
    bot_debug.log(__name__, f"telegram_bot => handle_dm => dm={dm}")
    abbot = Abbot(chat.id, "dm", dm.history)
    abbot.update_history_meta(message.text)
    bot_debug.log(__name__, f"chat_id={chat.id}, {user.username} dms with Abbot")
    answer = abbot.chat_completion()
    return await message.reply_text(answer)


async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, _ = update_data
    message_text: str = message.text
    args = message_text.split()
    if args[0] != "/fund":
        return error()
    amount: int = int(args[1])
    strike: Strike = init_payment_processor()
    description = f"Account topup for {chat.title}"
    response = strike.get_invoice(str(uuid.uuid1()), description, amount)
    invoice = try_get(response, "lnInvoice")
    if not invoice:
        return error()
    await message.reply_photo(qr_code(invoice), caption=description)
    await message.reply_markdown_v2(invoice)


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
                CommandHandler("fund", fund),
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
