import json
from io import open
from os import listdir
from os.path import abspath
from datetime import datetime

from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

from lib.utils import sender_is_group_admin, try_get
from lib.logger import debug_logger, error_logger
<<<<<<< HEAD
from lib.admin.admin_service import AdminService
from src.lib.abbot import GPT, Abbots
from lib.bot.config import BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM
=======
from lib.creator.admin_service import AdminService
from lib.gpt import GPT, Abbots
from lib.bot.constants import BOT_NAME, BOT_HANDLE, COUNT, THE_CREATOR, ATL_BITCOINER
>>>>>>> parent of 5d8f1ba (updates)

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")

ALL_ABBOTS = []

GROUP_CONTENT_FILE_PATH = abspath("src/data/chat/group/content")
GROUP_CONFIG_FILE_PATH = abspath("src/data/chat/group/config")
GROUP_CONTENT_FILES = sorted(listdir(GROUP_CONTENT_FILE_PATH))
GROUP_CONFIG_FILES = sorted(listdir(GROUP_CONFIG_FILE_PATH))

PRIVATE_CONTENT_FILE_PATH = abspath("src/data/chat/private/content")
PRIVATE_CONFIG_FILE_PATH = abspath("src/data/chat/private/config")
PRIVATE_CONTENT_FILES = sorted(listdir(PRIVATE_CONTENT_FILE_PATH))
PRIVATE_CONFIG_FILES = sorted(listdir(PRIVATE_CONFIG_FILE_PATH))

for content, config in zip(GROUP_CONTENT_FILES, GROUP_CONFIG_FILES):
    if ".jsonl" not in content or ".json" not in config:
        continue
    context = "group"
    chat_id = int(content.split(".")[0])
    name = f"{context}{BOT_NAME}{chat_id}"
    debug_logger.log(f"main => context={context} chat_id={chat_id} name={name}")
    group_abbot = GPT(
        name,
        BOT_TELEGRAM_HANDLE,
        BOT_CORE_SYSTEM,
        context,
        chat_id,
    )
    ALL_ABBOTS.append(group_abbot)

for content, config in zip(PRIVATE_CONTENT_FILES, PRIVATE_CONFIG_FILES):
    if ".jsonl" not in content or ".json" not in config:
        continue
    context = "private"
    chat_id = int(content.split(".")[0])
    name = f"{context}{BOT_NAME}{chat_id}"
    debug_logger.log(f"main => context={context} chat_id={chat_id} name={name}")
    group_abbot = GPT(
        name,
        BOT_TELEGRAM_HANDLE,
        BOT_CORE_SYSTEM,
        context,
        chat_id,
    )
    ALL_ABBOTS.append(group_abbot)

abbots: Abbots = Abbots(ALL_ABBOTS)
debug_logger.log(f"main abbots => {abbots.__str__()}")
admin = AdminService(THE_CREATOR, THE_CREATOR)
admin.status = "running"


@try_except
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message: Message = try_get(update, "message") or try_get(update, "effective_message")
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        if not message:
            debug_logger.log(f"handle_message => Missing Message: {message}")
            return
        if not chat:
            debug_logger.log(f"handle_message => Missing Chat: {chat}")
            return
        debug_logger.log(f"handle_message => Message={message}")
        debug_logger.log(f"handle_message => Chat={chat}")
        username = try_get(message, "from_user", "username")
        date = (try_get(message, "date", default=datetime.now())).strftime("%m/%d/%Y")
        name = try_get(chat, "first_name", default=username)
        chat_id = try_get(chat, "id")
        chat_type = try_get(chat, "type")
        message_text = try_get(message, "text")
        if not message_text:
            debug_logger.log(f"handle_message => Missing message text={message_text}")
            return
        debug_logger.log(f"handle_message => Message text={message_text}")
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        bot_context = "group"
        if is_group_chat or not is_private_chat:
            if BOT_TELEGRAM_HANDLE != "test_atl_bitlab_bot":
                chat_title: str = try_get(chat, "title", default="").lower().replace(" ", "")
                debug_logger.log(f"handle_message => not is_private_chat={not is_private_chat}")
                debug_logger.log(f"handle_message => is_group_chat={is_group_chat}")
                message_dump = json.dumps(
                    {
                        "id": chat_id,
                        "type": chat_type,
                        "title": chat_title,
                        "from": username,
                        "text": message_text,
                        "name": name,
                        "date": date,
                        "new": True,
                    }
                )
                debug_logger.log(f"handle_message => message_dump={message_dump}")
                raw_messages_jsonl = open(RAW_MESSAGE_JL_FILE, "a")
                raw_messages_jsonl.write(message_dump)
                raw_messages_jsonl.write("\n")
                raw_messages_jsonl.close()
        else:
            bot_context = "private"
            debug_logger.log(f"handle_message => is_private_chat={is_private_chat}")
        debug_logger.log(f"handle_message => bot_context={bot_context}")

        which_abbot: GPT = try_get(abbots, chat_id)
        if not which_abbot:
            which_bot_name = f"{bot_context}{BOT_NAME}{chat_id}"
            which_abbot = GPT(which_bot_name, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, bot_context, chat_id)

        which_name = try_get(which_abbot, "name")
        which_handle = try_get(which_abbot, "handle")
        which_history_len = len(try_get(which_abbot, "chat_history", default=[]))
        reply_to_message = try_get(message, "reply_to_message")
        reply_to_message_text = try_get(reply_to_message, "text", default="") or ""
        reply_to_message_from = try_get(reply_to_message, "from")
        reply_to_message_bot_username = try_get(reply_to_message_from, "username")

        full_handle = f"@{which_handle}"
        is_modulo_message = which_history_len % COUNT == 0
        reply_to_which_abbot = reply_to_message_bot_username == which_handle
        which_abbot.update_chat_history(dict(role="user", content=message_text))
        which_abbot.update_abbots(chat_id, which_abbot)
        if not which_abbot.get_started():
            if not which_abbot.get_sent_intro():
                debug_logger.log(f"handle_message => Abbot not started")
                debug_logger.log(f"which_abbot={which_abbot.__str__()}")
                intro_sent = which_abbot.introduce()
                debug_logger.log(f"intro_sent={intro_sent}")
                return await message.reply_text(
                    "Thank you for talking to Abbot (@atl_bitlab_bot), a bitcoiner bot for bitcoin communities, by the Atlanta Bitcoin community!\n"
                    "Abbot is meant to provide education to local bitcoin communities and help community organizers with various tasks.\n"
                    "- To start Abbot in a group chat, have a channel admin run /start\n"
                    "- To start Abbot in a DM, simply run /start.\n\n"
                    "By running /start, you agree to our Terms & policies: https://atlbitlab.com/abbot/policies.\n"
                    "If you have multiple bots in one channel, you may need to run /start@atl_bitlab_bot to avoid bot confusion!\n"
                    "If you have questions, concerns, feature requests or find bugs, please contact @nonni_io or @ATLBitLab on Telegram."
                )
        if is_group_chat:
            debug_logger.log(f"handle_message => group_in_name")
            debug_logger.log(f"handle_message => which_name={which_name}")
            if full_handle not in message_text:
                return
            if not reply_to_which_abbot:
                return
            if full_handle not in reply_to_message_text:
                return
            if is_modulo_message:
                return
            debug_logger.log(f"handle_message => All checks passed!")
            answer = which_abbot.chat_history_completion()
        else:
            debug_logger.log(f"handle_message => is private, not group_in_name")
            answer = which_abbot.chat_history_completion()

        if not answer:
            if which_abbot.sleep(10):
                await message.reply_text("Sorry, I was taking a quick nap 😴." "Still a lil groggy 🥴.")
            debug_logger.log(f"handle_message => which_abbot={which_abbot}")
            return await context.bot.send_message(
                chat_id=THE_CREATOR,
                text=f"{which_abbot.name} completion failed ⛔️: which_abbot={which_abbot} answer={answer}",
            )
        return await message.reply_text(answer)

    except Exception as exception:
        debug_logger.log(f"handle_message => Error={exception}")
        debug_logger.log(f"handle_message => which_abbot={which_abbot}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error={exception}")


@try_except
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


"""try:
    message: Message = try_get(update, "message") or try_get(
        update, "effective_message"
    )
    sender = try_get(message, "from_user", "username")
    message_text = try_get(message, "text")
    chat: Chat = try_get(update, "effective_chat") or try_get(message, "chat")
    chat_type = try_get(chat, "type")
    is_private_chat = chat_type == "private"
    is_group_chat = chat_type == "group"
    debug_logger.log(f"help => /help executed by {sender}")
    if is_group_chat:
        if f"@{BOT_TELEGRAM_HANDLE}" not in message_text:
            return await message.reply_text(
                f"For help, tag @{BOT_TELEGRAM_HANDLE} in the help command: e.g. /help @{BOT_TELEGRAM_HANDLE}",
            )
        return await message.reply_text(help_menu_message)
    if is_private_chat:
        await message.reply_text(help_menu_message)
except Exception as exception:
    error_logger.log(f"help => Error={exception}")
    await context.bot.send_message(
        chat_id=THE_CREATOR, text=f"Error={exception}"
    )
    raise exception"""


@try_except
async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "unleash:"
        message: Message = try_get(update, "message")
        chat: Chat = try_get(message, "chat")
        user: User = try_get(message, "from_user")
        if not message or not chat or not user:
            debug_logger.log(f"{fn} missing message: {message}")
            error_logger.log(f"{fn} missing chat: {chat}")
            error_logger.log(f"{fn} missing user: {user}")
            return
        debug_logger.log(f"{fn} message={message}")
        debug_logger.log(f"{fn} chat={chat}")
        debug_logger.log(f"{fn} user={user}")
        chat_type: str = try_get(chat, "type")
        chat_id: int = try_get(chat, "id")
        user_id: int = try_get(user, "id")
        username: int = try_get(user, "username")
        is_group_chat: bool = chat_type == "group"
        bot_context = "group"
        if is_group_chat:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id not in admin_ids:
                debug_logger.log(
                    f"{fn} => /unleash chat_id={chat_id} executed by username={username} user_id={user_id}"
                )
                return await update.message.reply_text("Forbidden: Admin only!")
        else:
            bot_context = "private"
        debug_logger.log(f"{fn} bot_context={bot_context}")
        abbot: GPT = try_get(abbots, chat_id)
        if not abbot:
            return await message.reply_text("")
        if not abbot.unleashed:
            unleashed = abbot.unleash()
            abbot.update_abbots(chat_id, abbot)
        debug_logger.log(f"{fn} {abbot.name} unleashed: {unleashed}")
        return await message.reply_text(f"{abbot.name} unleashed!")
    except Exception as exception:
        error_logger.log(f"{fn} Error={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error={exception}")
        raise exception


@try_except
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "rules:"
        message: Message = try_get(update, "message")
        chat: Chat = try_get(message, "chat")
        user: User = try_get(message, "from_user")
        if not message or not chat or not user:
            error_logger.log(f"{fn} missing message: {message}")
            error_logger.log(f"{fn} missing chat: {chat}")
            error_logger.log(f"{fn} missing user: {user}")
            return
        debug_logger.log(f"{fn} message={message}")
        debug_logger.log(f"{fn} chat={chat}")
        debug_logger.log(f"{fn} user={user}")
        chat_id: int = try_get(chat, "id")
        user_id: int = try_get(user, "id")
        username: int = try_get(user, "username")
        chat_type: str = try_get(chat, "type")
        chat_title: str = try_get(chat, "title")
        if not chat_id or not chat_type or not user_id:
            error_logger.log(f"{fn} missing chat id: {chat_id}")
            error_logger.log(f"{fn} missing chat type: {chat_type}")
            error_logger.log(f"{fn} missing user id: {user_id}")
            return
        debug_logger.log(f"{fn} chat_id={chat_id}")
        debug_logger.log(f"{fn} chat_type={chat_type}")
        debug_logger.log(f"{fn} user_id={user_id}")
        debug_logger.log(f"{fn} executed by username={username} user_id={user_id}")
        await message.reply_text(
            "Hey! The name's Abbot but you can think of me as your go-to guide for all things Bitcoin. AKA the virtual Bitcoin whisperer. 😉\n\n"
            "Here's the lowdown on how to get my attention: \n\n"
            "1. Slap an @atl_bitlab_bot before your message in the group chat - I'll come running to answer. \n"
            "2. Feel more comfortable replying directly to my messages? Go ahead! I'm all ears.. err.. code. \n"
            "3. Fancy a one-on-one chat? Slide into my DMs. \n\n"
            "Now, enough with the rules! Let's dive into the world of Bitcoin together! \n\n"
            "Ready. Set. Stack Sats! 🚀"
        )
    except Exception as exception:
        error_logger.log(f"statuses => Error={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error={exception}")
        raise exception


@try_except
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "start:"
        message: Message = try_get(update, "message")
        chat: Chat = try_get(message, "chat")
        user: User = try_get(message, "from_user")
        if not message or not chat or not user:
            error_logger.log(f"{fn} missing message: {message}")
            error_logger.log(f"{fn} missing chat: {chat}")
            error_logger.log(f"{fn} missing user: {user}")
            return
        debug_logger.log(f"{fn} message={message}")
        debug_logger.log(f"{fn} chat={chat}")
        debug_logger.log(f"{fn} user={user}")
        chat_id: int = try_get(chat, "id")
        user_id: int = try_get(user, "id")
        chat_type: str = try_get(chat, "type")
        chat_title: str = try_get(chat, "title")
        if not chat_id or not chat_type or not user_id:
            error_logger.log(f"{fn} missing chat id: {chat_id}")
            error_logger.log(f"{fn} missing chat type: {chat_type}")
            error_logger.log(f"{fn} missing user id: {user_id}")
            return
        debug_logger.log(f"{fn} chat_id={chat_id}")
        debug_logger.log(f"{fn} chat_type={chat_type}")
        debug_logger.log(f"{fn} user_id={user_id}")
        bot_context = "group"
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        if is_group_chat:
            is_admin = await sender_is_group_admin(context)
            if not is_admin:
                return await message.reply_text("Forbidden: Admin only!")
        else:
            bot_context = "private"
            debug_logger.log(f"{fn} is_private_chat={is_private_chat}")
        debug_logger.log(f"{fn} bot_context={bot_context}")
        abbot: GPT = try_get(abbots, chat_id)
        if not abbot:
            abbot: GPT = GPT(
                f"{bot_context}{BOT_NAME}{chat_id}", BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, bot_context, chat_id
            )
        abbot_dict: dict = abbot.to_dict()
        if abbot.started:
            return await message.reply_text("Abbot already started!")
        started = abbot.start()
        debug_logger.log(f"{fn} abbot={abbot_dict} started={started}")
        await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while we unplug {BOT_NAME} from the Matrix")
        response = abbot.chat_history_completion()
        if not response:
            return await context.bot.send_message(
                chat_id=THE_CREATOR,
                text=f"chat_title={chat_title} chat_id={chat_id} response={response}",
            )
        await message.reply_text(response)
    except Exception as exception:
        error_logger.log(f"{fn} exception={exception}")
        error_msg = f"chat_title={chat_title} chat_id={chat_id} response={response}"
        await context.bot.send_message(chat_id=THE_CREATOR, text=error_msg)


@try_except
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "stop:"
        message: Message = try_get(update, "message")
        chat: Chat = try_get(message, "chat")
        user: User = try_get(message, "from_user")
        if not message or not chat or not user:
            error_logger.log(f"{fn} missing message: {message}")
            error_logger.log(f"{fn} missing chat: {chat}")
            error_logger.log(f"{fn} missing user: {user}")
            return
        debug_logger.log(f"{fn} message={message}")
        debug_logger.log(f"{fn} chat={chat}")
        debug_logger.log(f"{fn} user={user}")
        chat_id: int = try_get(chat, "id")
        user_id: int = try_get(user, "id")
        chat_type: str = try_get(chat, "type")
        chat_title: str = try_get(chat, "title")
        if not chat_id or not chat_type or not user_id:
            error_logger.log(f"{fn} missing chat id: {chat_id}")
            error_logger.log(f"{fn} missing chat type: {chat_type}")
            error_logger.log(f"{fn} missing user id: {user_id}")
            return
        debug_logger.log(f"{fn} chat_id={chat_id}")
        debug_logger.log(f"{fn} chat_type={chat_type}")
        debug_logger.log(f"{fn} user_id={user_id}")
        bot_context = "group"
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        if is_group_chat:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id not in admin_ids:
                return await update.message.reply_text("Forbidden: Admin only!")
        else:
            bot_context = "private"
            debug_logger.log(f"{fn} is_private_chat={is_private_chat}")
        debug_logger.log(f"{fn} bot_context={bot_context}")
        abbot: GPT = try_get(abbots, chat_id)
        if not abbot:
            abbot: GPT = GPT(
                f"{bot_context}{BOT_NAME}{chat_id}", BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, bot_context, chat_id
            )
        debug_logger.log(f"{fn} abbot: {json.dumps(abbot.to_dict())}")
        if not abbot.started:
            await message.reply_text("Abbot isn't started yet! Have an admin run /start")
            return await context.bot.send_message(
                chat_id=THE_CREATOR, text=f"chat_title={chat_title} chat_id={chat_id}"
            )
        started = abbot.stop()
        if not started:
            raise Exception(f"Not started! started={started}")
        await message.reply_text("Thanks for using Abbot! To restart, use the /start command at any time.")
    except Exception as exception:
        error_logger.log(f"{fn} exception={exception}")
        error_msg = f"chat_title={chat_title} chat_id={chat_id}"
        await context.bot.send_message(chat_id=THE_CREATOR, text=error_msg)


@try_except
async def admin_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "_admin_plugin:"
        chat_id: int = try_get(update, "message", "chat", "id")
        user_id: int = try_get(update, "message", "from_user", "id")
        if user_id != THE_CREATOR:
            return
        admin: AdminService = AdminService(user_id, chat_id)
        admin.stop_service()
    except Exception as exception:
        error_logger.log(f"{fn} => exception={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"{fn} exception: {exception}")
        raise exception


@try_except
async def admin_unplug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "admin_unplug:"
        chat_id: int = try_get(update, "message", "chat", "id")
        user_id: int = try_get(update, "message", "from_user", "id")

        admin: AdminService = AdminService(user_id, chat_id)
        admin.start_service()
    except Exception as exception:
        error_logger.log(f"{fn} => exception={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"{fn} exception: {exception}")


@try_except
async def admin_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as exception:
        error_logger.log(f"{fn} => exception={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"{fn} exception: {exception}")
        raise exception


@try_except
async def admin_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as exception:
        error_logger.log(f"{fn} => exception={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"{fn} exception: {exception}")


@try_except
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "admin_status:"
        message: Message = try_get(update, "message")
        user: User = try_get(message, "from_user")
        user_id: int = try_get(user, "id")
        if user_id != THE_CREATOR:
            return
        abbots_dict: dict = abbots.get_abbots()
        for bot in abbots_dict:
            abbot: GPT = bot
            status_data = json.dumps(abbot.get_state(), indent=4)
            debug_logger.log(f"statuses => {abbot.name} status_data={status_data}")
            await message.reply_text(status_data)
    except Exception as exception:
        error_logger.log(f"{fn} => exception={exception}")
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"{fn} exception: {exception}")
