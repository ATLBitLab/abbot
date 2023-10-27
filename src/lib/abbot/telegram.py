import json
from io import open
from os import listdir
from os.path import abspath

from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)

from constants import HELP_MENU, THE_CREATOR
from lib.logger import debug_logger, error_logger
from lib.utils import sender_is_group_admin, try_get

from lib.admin.admin_service import AdminService

from lib.abbot.bot import Abbot, Bots
from lib.abbot.exceptions.exception import try_except, AbbotException
from lib.abbot.utils import (
    parse_chat,
    parse_chat_data,
    parse_message,
    parse_message_data,
    parse_user,
    parse_user_data,
    squawk_error,
    successful,
)
from lib.abbot.exceptions.exception import try_except, AbbotException
from lib.abbot.config import BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_TELEGRAM_TOKEN, BOT_CORE_SYSTEM

# context.args
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
    group_abbot = Abbot(
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
    private_abbot = Abbot(
        name,
        BOT_TELEGRAM_HANDLE,
        BOT_CORE_SYSTEM,
        context,
        chat_id,
    )
    ALL_ABBOTS.append(private_abbot)

abbots: Bots = Bots(ALL_ABBOTS)
admin = AdminService(THE_CREATOR, THE_CREATOR)
admin.status = "running"


@try_except_pass
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "handle_message:"
    if not update or not context:
        return error_logger.log(f"{fn} No update or context")

    debug_logger.log(f"{fn} Update={update}")
    debug_logger.log(f"{fn} Context={context}")

    response: dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        return await squawk_error(message, context)

    message_data: dict = parse_message_data(message)
    message_text: str = try_get(message_data, "text")
    message_date: str = try_get(message_data, "date")

    response: dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(message, "data")
        return await squawk_error(error_message, context)
    chat_data: dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_type: str = try_get(chat_data, "type")
    is_private_chat = chat_type == "private"
    is_group_chat = chat_type == "group"
    chat_title: str = try_get(chat_data, "title", default="private" if is_private_chat else None)

    response: dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        return await squawk_error(user, context)
    user_data: dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")

    # log all data for debugging
    abbot_context = "group"

    all_data: dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")

    abbot_message = dict(role="user", content=message_text)
    if is_group_chat and "test" not in BOT_TELEGRAM_HANDLE:
        debug_logger.log(f"{fn} is_group_chat={is_group_chat}")
        debug_logger.log(f"{fn} test not in BOT_TELEGRAM_HANDLE={BOT_TELEGRAM_HANDLE}")
        message_dump = json.dumps(
            {"message": {**message_data}, "chat": {**chat_data}, "user": {**user_data}, "abbot": abbot_message}
        )
        debug_logger.log(f"{fn} message_dump={message_dump}")
        raw_messages_jsonl = open(RAW_MESSAGE_JL_FILE, "a")
        raw_messages_jsonl.write(message_dump)
        raw_messages_jsonl.write("\n")
        raw_messages_jsonl.close()
    else:
        abbot_context = "private"
        debug_logger.log(f"{fn} is_private_chat={is_private_chat}")
    debug_logger.log(f"{fn} abbot_context={abbot_context}")

    abbot: Abbot = try_get(abbots, chat_id)
    if not abbot:
        name = f"{abbot_context}{BOT_NAME}{chat_id}"
        abbot = Abbot(name, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, abbot_context, chat_id)
        abbots.update_abbots(chat_id, abbot)

    # not_introduced: bool = abbot.is_forgotten()
    # if not_introduced:
    #     debug_logger.log(f"{fn} Abbot not introduced!")
    #     abbot.introduce()
    #     introduced = abbot.is_introduced()
    #     debug_logger.log(f"introduced={introduced}")
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
    #     debug_logger.log(f"{fn} Abbot introduced!")
    #     debug_logger.log(f"{fn} Abbot not started!")
    #     return

    handle: str = abbot.handle
    message_reply = try_get(message, "reply_to_message")
    message_reply_text = try_get(message_reply, "text")
    message_reply_from = try_get(message_reply, "from")
    replied_to_abbot = try_get(message_reply_from, "username") == handle
    if is_private_chat:
        abbot.update_chat_history(abbot_message)
        debug_logger.log(f"{fn} is private, not group_in_name")
        answer = abbot.chat_history_completion()
    else:
        chat_history_len: int = abbot.chat_history_len
        is_unleashed, count = abbot.is_unleashed()
        debug_logger.log(f"{fn} group_in_name: name={abbot.name}")
        if handle not in message_text and handle not in message_reply_text:
            debug_logger.log(f"{fn} handle not in message_text or message_reply_text")
            return
        if not replied_to_abbot:
            debug_logger.log(f"{fn} not replied_to_abbot!")
            return
        if not is_unleashed or not count:
            debug_logger.log(f"{fn} not is_unleashed or not count")
            return
        if chat_history_len % count != 0:
            debug_logger.log(f"{fn} chat_history_len % count != 0!")
            return
        debug_logger.log(f"{fn} All checks passed!")
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
    #     debug_logger.log(f"{fn} answer={answer}")
    #     if answer:
    #         continue
    #     i += 1
    # if not answer:
    #     return await context.bot.send_message(
    #         chat_id=user_id, text="Sorry, I seem to have bugged out bug 🐜 please contact @nonni_io for help."
    #     )
    return await message.reply_text(answer)


@try_except_pass
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "help:"
    message: Message = parse_message(update)
    chat: Chat = parse_chat(update, message)
    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    message_data: dict = parse_message_data(message)
    chat_data: dict = parse_chat_data(chat)
    # log all data for debugging
    all_data: dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")
    await message.reply_text(HELP_MENU)


@try_except_pass
async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "unleash:"
    response: dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        data = message
        return await squawk_error(data, context)
    message_data: dict = parse_message_data(message)

    response: dict = parse_chat(update, message)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        data = chat
        return await squawk_error(data, context)
    chat_data: dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_title: str = try_get(chat_data, "title")
    chat_type: str = try_get(chat_data, "type")

    response: dict = parse_user(message)
    user: User = try_get(response, "data")
    if not successful(response):
        data = user
        return await squawk_error(data, context)
    user_data: dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")

    is_group_chat: bool = chat_type == "group"
    is_private_chat: bool = chat_type == "private"
    # log all data for debugging
    all_data: dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")

    abbot_context = "group"
    if is_private_chat:
        abbot_context = "private"
    elif is_group_chat:
        is_admin = await sender_is_group_admin(context, chat_id, user_id)
        if not is_admin:
            return await message.reply_text(f"Forbidden: Admin only. {username} is not an admin of {chat_title}.")

    debug_logger.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = try_get(abbots, chat_id)
    if not abbot:
        # TODO: dont do this
        raise AbbotException(f"{fn} Abbot missing!")
    elif abbot.is_stopped():
        return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    unleashed, count = abbot.is_unleashed()
    if unleashed:
        return await message.reply_text(f"I'm already unleashed for {chat_title}! To leash me, please run /leash!")

    abbot.unleash()
    abbot.update_abbots(chat_id, abbot)
    unleashed, count = abbot.is_unleashed()
    debug_logger.log(f"{fn} {abbot.name} unleashed={unleashed}")
    return await message.reply_text(
        f"I have been unleashed! I will now respond every {count} messages until"
        "you run /leash or /unleash <insert_new_number> (e.g. /unleash 10)"
    )


@try_except_pass
async def leash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "leash:"
    message: Message = parse_message(update)
    message_data: dict = parse_message_data(message)

    chat: Chat = parse_chat(update, message)
    chat_data: dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_title: str = try_get(chat_data, "title")
    chat_type: str = try_get(chat_data, "type")

    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")

    is_group_chat: bool = chat_type == "group"
    is_private_chat: bool = chat_type == "private"
    abbot_context = "group"
    # log all data for debugging
    all_data: dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")
    if is_private_chat:
        abbot_context = "private"
    elif is_group_chat:
        is_admin = await sender_is_group_admin(context, chat_id, user_id)
        if not is_admin:
            return await message.reply_text(f"Forbidden: Admin only. {username} is not an admin of {chat_title}.")
    debug_logger.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = try_get(abbots, chat_id)
    if not abbot:
        # TODO: dont do this
        raise AbbotException(f"{fn} Abbot missing!")
    elif abbot.is_stopped():
        return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    leashed, count = abbot.is_leashed()
    if leashed:
        return await message.reply_text(f"I'm already leashed for {chat_title}! To unleash me, please run /leash!")

    abbot.leash()
    leashed, count = abbot.is_leashed()
    abbot.update_abbots(chat_id, abbot)
    debug_logger.log(f"{fn} {abbot.name} leashed={leashed}")
    return await message.reply_text(
        f"I have been leashed! To unleash me again, run /unleash or /unleash <insert_new_number> (e.g. /unleash 10)"
    )


@try_except_pass
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


@try_except_pass
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "start:"
    response: dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        return squawk_error(message, context)

    message_data: dict = parse_message_data(message)
    message_text: str = try_get(message_data, "text")
    message_date: str = try_get(message_data, "date")

    response: dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(message, "data")
        return squawk_error(error_message, context)
    chat_data: dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_type: str = try_get(chat_data, "type")
    is_private_chat = chat_type == "private"
    is_group_chat = chat_type == "group"
    chat_title: str = try_get(chat_data, "title", default="private" if is_private_chat else None)

    response: dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        return await squawk_error(user, context)
    user_data: dict = parse_user_data(user)

    # log all data for debugging
    abbot_context = "group"
    all_data: dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")

    abbot_context = "group"
    is_private_chat = chat_type == "private"
    is_group_chat = chat_type == "group"
    if is_group_chat:
        is_admin = await sender_is_group_admin(context)
        if not is_admin:
            return await message.reply_text("Forbidden: Admin only!")
    else:
        abbot_context = "private"
        debug_logger.log(f"{fn} is_private_chat={is_private_chat}")
    debug_logger.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = try_get(abbots, chat_id)
    if not abbot:
        name = f"{abbot_context}{BOT_NAME}{chat_id}"
        abbot: Abbot = Abbot(name, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, abbot_context, chat_id)
    elif abbot.is_started():
        return await message.reply_text("Abbot already started!")
    abbot.start()
    started = abbot.is_started()
    debug_logger.log(f"{fn} abbot={abbot.to_dict()} started={started}")
    await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while we unplug {BOT_NAME} from the Matrix")
    response = abbot.chat_history_completion()
    if not response:
        return await context.bot.send_message(
            chat_id=THE_CREATOR,
            text=f"chat_title={chat_title} chat_id={chat_id}",
        )
    await message.reply_text(response)


@try_except_pass
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    abbot_context = "group"
    is_private_chat = chat_type == "private"
    is_group_chat = chat_type == "group"
    if is_group_chat:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in admins]
        if user_id not in admin_ids:
            return await update.message.reply_text("Forbidden: Admin only!")
    else:
        abbot_context = "private"
        debug_logger.log(f"{fn} is_private_chat={is_private_chat}")
    debug_logger.log(f"{fn} abbot_context={abbot_context}")
    abbot: Abbot = try_get(abbots, chat_id)
    if not abbot:
        abbot: Abbot = Abbot(
            f"{abbot_context}{BOT_NAME}{chat_id}", BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, abbot_context, chat_id
        )
    debug_logger.log(f"{fn} abbot: {json.dumps(abbot.to_dict())}")
    if not abbot.started:
        await message.reply_text("Abbot isn't started yet! Have an admin run /start")
        return await context.bot.send_message(chat_id=THE_CREATOR, text=f"chat_title={chat_title} chat_id={chat_id}")
    started = abbot.stop()
    if not started:
        raise Exception(f"Not started! started={started}")
    await message.reply_text("Thanks for using Abbot! To restart, use the /start command at any time.")


@try_except_pass
async def admin_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "_admin_plugin:"
    chat_id: int = try_get(update, "message", "chat", "id")
    user_id: int = try_get(update, "message", "from_user", "id")
    if user_id != THE_CREATOR:
        return
    admin: AdminService = AdminService(user_id, chat_id)
    admin.stop_service()


@try_except_pass
async def admin_unplug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_unplug:"
    chat_id: int = try_get(update, "message", "chat", "id")
    user_id: int = try_get(update, "message", "from_user", "id")

    admin: AdminService = AdminService(user_id, chat_id)
    admin.start_service()


@try_except_pass
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


@try_except_pass
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


@try_except_pass
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "admin_status:"
    message: Message = try_get(update, "message")
    user: User = try_get(message, "from_user")
    user_id: int = try_get(user, "id")
    if user_id != THE_CREATOR:
        return
    abbots_dict: dict = abbots.get_abbots()
    for bot in abbots_dict:
        abbot: Abbot = bot
        status_data = json.dumps(abbot.get_state(), indent=4)
        debug_logger.log(f"statuses => {abbot.name} status_data={status_data}")
        await message.reply_text(status_data)


def run():
    debug_logger.log(f"Initializing telegram {BOT_NAME} @{BOT_TELEGRAM_HANDLE}")
    APPLICATION = ApplicationBuilder().token(BOT_TELEGRAM_TOKEN).build()
    debug_logger.log(f"Telegram {BOT_NAME} @{BOT_TELEGRAM_HANDLE} Initialized")

    _unplug_handler = CommandHandler("unplug", admin_unplug)
    _plugin_handler = CommandHandler("plugin", admin_plugin)
    _kill_handler = CommandHandler("kill", admin_kill)
    _nap_handler = CommandHandler("nap", admin_nap)
    _status_handler = CommandHandler("status", admin_status)

    APPLICATION.add_handler(_unplug_handler)
    APPLICATION.add_handler(_plugin_handler)
    APPLICATION.add_handler(_kill_handler)
    APPLICATION.add_handler(_nap_handler)
    APPLICATION.add_handler(_status_handler)

    help_handler = CommandHandler("help", help)
    rules_handler = CommandHandler("rules", rules)
    start_handler = CommandHandler("start", start)
    stop_handler = CommandHandler("stop", stop)
    unleash_handler = CommandHandler("unleash", unleash)
    leash_handler = CommandHandler("leash", leash)

    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(rules_handler)
    APPLICATION.add_handler(start_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(unleash_handler)
    APPLICATION.add_handler(leash_handler)

    # TODO: define different message handlers such as Mention() or Reply() if exists
    # BaseFilter should run first and do 1 thing: store the message and setup the telegram stuff
    # Mention, ReplyToBot and Unleash fitlers should reply with a completion
    message_handler = MessageHandler(BaseFilter(), handle_message)
    APPLICATION.add_handler(message_handler)

    debug_logger.log(f"Telegram {BOT_NAME} @{BOT_TELEGRAM_HANDLE} Polling")
    APPLICATION.run_polling()
