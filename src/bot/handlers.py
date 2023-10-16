import json
from io import open
from datetime import datetime
from os.path import abspath

from telegram.ext import ContextTypes
from telegram import Chat, Message, Update, User
from abbot.exceptions.AbbitException import try_except

from config import (
    ORG_CHAT_ID,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    BOT_CORE_SYSTEM,
    ORG_CHAT_TITLE,
    ORG_CHAT_HISTORY_FILEPATH,
    bot_response,
)
from utils import (
    get_chat_admins,
    parse_message,
    parse_message_data,
    parse_chat,
    parse_chat_data,
    parse_user,
    parse_user_data,
)
from bot.abbot import Abbot
from lib.utils import try_get
from constants import HELP_MENU, THE_CREATOR
from lib.logger import debug_logger, error_logger

now = datetime.now()
abbot: Abbot = Abbot(BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, ORG_CHAT_ID)
ORG_CHAT_FILEPATH = abspath(ORG_CHAT_HISTORY_FILEPATH)
MATRIX_IMG_FILEPATH = abspath("assets/unplugging_matrix.jpg")


@try_except
async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "handle_mention:"
    debug_logger.log(update)
    debug_logger.log(context)
    answer = abbot.chat_history_completion()
    if not answer:
        debug_logger.log(f"{fn} abbot={abbot}")
        update.message.reply_text("⛔️ An error occured, contact @nonni_io for help🥴")
        return await context.bot.send_message(
            chat_id=THE_CREATOR,
            text=f"{abbot.name} completion failed ⛔️: abbot={abbot} answer={answer}",
        )
    return await update.message.reply_text(answer)


@try_except
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "handle_message:"
    message: Message = parse_message(update)
    message_data: dict = parse_message_data(message)
    message_text: str = try_get(message_data, "text")
    message_date: str = try_get(message_data, "date")
    debug_logger.log(f"{fn} message={message}")
    debug_logger.log(f"{fn} message_data={message_data}")
    debug_logger.log(f"{fn} message_text={message_text}")
    debug_logger.log(f"{fn} message_date={message_date}")
    chat: Chat = parse_chat(update, message)
    chat_data: dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "chat_id", default=ORG_CHAT_ID)
    chat_title: str = try_get(chat_data, "chat_title", default=ORG_CHAT_TITLE)
    debug_logger.log(f"{fn} chat={chat}")
    debug_logger.log(f"{fn} chat_data={chat_data}")
    debug_logger.log(f"{fn} chat_id={chat_id}")
    debug_logger.log(f"{fn} chat_title={chat_title}")
    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")
    debug_logger.log(f"{fn} user={user}")
    debug_logger.log(f"{fn} user_data={user_data}")
    debug_logger.log(f"{fn} user_id={user_id}")
    debug_logger.log(f"{fn} username={username}")
    blixt_message = json.dumps(
        {
            "message_text": message_text,
            "message_date": message_date,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "user_id": user_id,
            "username": username,
        }
    )
    debug_logger.log(f"{fn} blixt_message={blixt_message}")
    blixt_chat = open(ORG_CHAT_FILEPATH, "a")
    blixt_chat.write(blixt_message + "\n")
    blixt_chat.close()
    reply_to_message = try_get(message, "reply_to_message")
    reply_to_message_text = try_get(reply_to_message, "text", default="") or ""
    reply_to_message_from = try_get(reply_to_message, "from")
    reply_to_message_from_bot = try_get(reply_to_message_from, "is_bot")
    reply_to_message_bot_handle = try_get(reply_to_message_from, "username")
    debug_logger.log(f"{fn} reply_to_message={reply_to_message}")
    debug_logger.log(f"{fn} reply_to_message_text={reply_to_message_text}")
    debug_logger.log(f"{fn} reply_to_message_from={reply_to_message_from}")
    debug_logger.log(f"{fn} reply_from_bot={reply_to_message_from_bot}")
    debug_logger.log(f"{fn} reply_bot_username={reply_to_message_bot_handle}")
    abbit_tagged = BOT_TELEGRAM_HANDLE in message_text
    reply_to_abbit = reply_to_message_bot_handle == abbot.handle
    started, sent_intro = abbot.status()
    if abbit_tagged or reply_to_abbit:
        if not started and not sent_intro:
            debug_logger.log(f"{fn} Abbot not ready")
            debug_logger.log(f"{fn} sent_intro={sent_intro}")
            debug_logger.log(f"{fn} started={started}")
            debug_logger.log(f"{fn} abbot={abbot.__str__()}")
            hello = abbot.hello()
            hello = "".join(hello)
            debug_logger.log(f"{fn} hello={hello}")
            return await update.message.reply_text(hello)
        elif started and sent_intro:
            abbit_message = {
                "role": "user",
                "content": f"{message_text} from {username} on {message_date}",
            }
            debug_logger.log(f"{fn} abbit_message={abbit_message}")
            abbot.update_chat_history(abbit_message)

            return await handle_mention(update, context)
    elif chat_his:



@try_except
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "help =>"
    message: Message = parse_message(update)
    message_data: dict = parse_message_data(message)
    chat: Chat = parse_chat(update, message)
    chat_data: int = parse_chat_data(chat)
    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    all_data = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")
    return await update.message.reply_text(HELP_MENU)


@try_except
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "start:"
    message: Message = parse_message(update)
    message_data: dict = parse_message_data(message)
    message_text: str = try_get(message_data, "text")
    message_date: str = try_get(message_data, "date")
    chat: Chat = parse_chat(update, message)
    chat_data: dict = parse_chat_data(chat)
    chat_id = try_get(chat_data, "chat_id", default=ORG_CHAT_ID)
    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    user_id = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")
    chat_admin_data: dict = get_chat_admins(chat_id, context)
    chat_admin_ids = try_get(chat_admin_data, "ids")
    chat_admin_usernames = try_get(chat_admin_data, "usernames")
    is_chat_admin = user_id in chat_admin_ids or username in chat_admin_usernames
    all_data = dict(**message_data, **chat_data, **user_data, **chat_admin_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")
    if not is_chat_admin:
        return await update.message.reply_text(bot_response("forbidden", 0))
    start_intro = abbot.start_command()
    if not start_intro:
        msg = f"started={abbot.started} sent_intro={abbot.sent_intro}"
        error_logger.log(msg)
        raise Exception(f"failed to start: {msg}")
    abbit_message = dict(
        role="user",
        content=f"{message_text} from {username} on {message_date}",
    )
    debug_logger.log(f"{fn} abbit_message={abbit_message}")
    abbot.update_chat_history(abbit_message)
    await message.reply_photo(
        MATRIX_IMG_FILEPATH, f"Unplugging {BOT_NAME} from the Matrix"
    )
    response = abbot.chat_history_completion()
    if not response:
        abbot.stop()
        response = f"{abbot.name} start failed ⛔️! {bot_response('fail', 0)}."
        abbit_str = abbot.__str__()
        error_logger.log(f"{fn} abbot={abbit_str}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"abbot={abbit_str} response={response}"
        )
    await message.reply_text(response)


@try_except
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "stop:"
    # message data
    message: Message = parse_message(update)
    message_data: dict = parse_message_data(message)
    # chat data
    chat: Chat = parse_chat(update, message)
    chat_data: dict = parse_chat_data(chat)
    chat_id = try_get(chat_data, "chat_id", default=ORG_CHAT_ID)
    # user data
    user: User = parse_user(message)
    user_data: dict = parse_user_data(user)
    user_id = try_get(user_data, "user_id")
    username: str = try_get(user_data, "username")
    # chat admin data
    chat_admin_data: dict = get_chat_admins(chat_id, context)
    chat_admin_ids = try_get(chat_admin_data, "ids")
    chat_admin_usernames = try_get(chat_admin_data, "usernames")
    is_chat_admin = user_id in chat_admin_ids or username in chat_admin_usernames
    # log all data for debugging
    all_data = dict(**message_data, **chat_data, **user_data, **chat_admin_data)
    for k, v in all_data.items():
        debug_logger.log(f"{fn} {k}={v}")
    # check sender is chat admin
    if not is_chat_admin:
        return await update.message.reply_text(bot_response("forbidden", 0))
    started = abbot.started
    if not started:
        debug_logger.log(f"{fn} Abbot not started! abbot.started={abbot.started}")
        return await message.reply_text(
            f"/stop failed! Abbot not started! Have you run /start yet?"
            "If so, please try again later or contact @nonni_io"
        )
    stopped = abbot.stop_command()
    if not stopped:
        err_msg = f"{fn} not stopped! abbot={abbot}, stopped={stopped}"
        error_logger.log(err_msg)
        await message.reply_text(
            "/stop failed! Something went wrong."
            "Please try again later or contact @nonni_io"
        )
        return await context.bot.send_message(chat_id=THE_CREATOR, text=err_msg)
    await message.reply_photo(
        f"Pluggin {BOT_NAME} back into the matrix."
        "To restart, have an admin run the /start command."
    )
