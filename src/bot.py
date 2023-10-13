import json
from datetime import datetime

from bot_utils import deconstruct_error, parse_update, parse_update_data

now = datetime.now()
from os.path import abspath
from functools import wraps
from io import open
from random import randrange

from constants import (
    THE_CREATOR,
    OPTINOUT_FILEPATH,
    SUPER_DOOPER_ADMINS,
    CHEEKY_RESPONSES,
)
from bot_config import (
    ORG_CHAT_ID,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    BOT_CORE_SYSTEM,
    ORG_CHAT_TITLE,
)
from lib.abbit import Abbit

abbit: Abbit = Abbit(BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_CORE_SYSTEM, ORG_CHAT_ID)
BLIXT_CHAT_HISTORY = abspath("src/data/blixt.jsonl")

from lib.logger import debug_logger, error_logger

MESSAGE_LOG_FILE = abspath("src/data/message_debug.py")

from lib.utils import (
    try_get,
    try_get_telegram_message_data,
)
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug_logger.log(update)
    debug_logger.log(context)
    answer = abbit.chat_history_completion()
    if not answer:
        stopped = abbit.stop()
        debug_logger.log(f"handle_message => abbit={abbit} stopped={stopped}")
        update.message.reply_text("Something went wrong. Please try again or contact @ATLBitLab")
        return await context.bot.send_message(
            chat_id=THE_CREATOR,
            text=f"{abbit.name} completion failed ⛔️: abbit={abbit} stopped={stopped} answer={answer}",
        )
    return await update.message.reply_text(answer)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        debug_logger.log(f"handle_message => Raw update={update}")
        mpy = open(MESSAGE_LOG_FILE, "a")
        mpy.write(update.to_json())
        mpy.write("\n")
        mpy.close()

        success, message, chat, user = parse_update(update)
        if not success:
            raise Exception(f"parse_update: message={message} chat={chat} user={user}")
        debug_logger.log(f"start => message={message}")
        debug_logger.log(f"start => chat={chat}")
        debug_logger.log(f"start => user={user}")

        success, message_text, message_date, user_id, username = parse_update_data(message, chat, user)
        if not success:
            data = f"message={message}" f"chat={chat}" f"user={user}"
            raise Exception(
                f"parse_update_data: success={success} {data}"
            )
        debug_logger.log(f"start => message_text={message_text}")
        debug_logger.log(f"start => message_date={message_date}")
        debug_logger.log(f"start => user_id={user_id}")
        debug_logger.log(f"start => username={username}")

        message_dump = json.dumps(
            {
                "id": ORG_CHAT_ID,
                "title": ORG_CHAT_TITLE,
                "from": username,
                "text": message_text,
                "date": message_date,
                "new": True,
            }
        )
        debug_logger.log(f"handle_message => message_dump={message_dump}")
        blixt_chat = open(BLIXT_CHAT_HISTORY, "a")
        blixt_chat.write(message_dump)
        blixt_chat.write("\n")
        blixt_chat.close()

        started, sent_intro = abbit.status()
        
        reply_to_message = try_get(message, "reply_to_message")
        reply_to_message_text = try_get(reply_to_message, "text", default="") or ""
        reply_to_message_from = try_get(reply_to_message, "from")
        reply_to_message_from_bot = try_get(reply_to_message_from, "is_bot")
        reply_to_message_bot_handle = try_get(reply_to_message_from, "username")

        debug_logger.log(f"handle_message => reply_to_message={reply_to_message}")
        debug_logger.log(
            f"handle_message => reply_to_message_text={reply_to_message_text}"
        )
        debug_logger.log(
            f"handle_message => reply_to_message_from={reply_to_message_from}"
        )
        debug_logger.log(
            f"handle_message => reply_from_bot={reply_to_message_from_bot}"
        )
        debug_logger.log(
            f"handle_message => reply_bot_username={reply_to_message_bot_handle}"
        )

        started, sent_intro = abbit.status()
        if not started and not sent_intro:
            debug_logger.log(f"handle_message => Abbot not started")
            debug_logger.log(f"started={started}")
            debug_logger.log(f"abbit={abbit.__str__()}")
            abbit.hello()
            return await message.reply_text(
                "Hello! Thank you for talking to Abbot (@atl_bitlab_bot), A Bitcoin Bot for local communities! \n\n"
                "Abbot is meant to provide education to local bitcoin communities and help community organizers with various tasks. \n\n"
                "To start Abbot in a group chat, have a channel admin run /start \n\n"
                "To start Abbot in a DM, simply run /start. \n\n"
                "By running /start, you agree to our Terms & policies: https://atlbitlab.com/abbot/policies. \n\n"
                "If you have multiple bots in one channel, you may need to run /start @atl_bitlab_bot to avoid bot confusion! \n\n"
                "Thank you for using Abbot! We hope you enjoy your experience! \n\n"
                "If you have questions, concerns, feature requests or find bugs, please contact @nonni_io or @ATLBitLab on Telegram."
            )

        abbit.update_chat_history(dict(role="user", content=message_text))
        abbit_tagged = BOT_TELEGRAM_HANDLE in message_text
        reply_to_abbit = reply_to_message_bot_handle == abbit.handle
        if abbit_tagged or reply_to_abbit:
            handle_mention(update, context)
    except Exception as exception:
        status = abbit.status()
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(
            f"handle_message => Error={exception}, ErrorMessage={error_msg}"
        )
        error_logger.log(f"handle_message => abbit={abbit} status={status}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message, _, user: (Message, Chat, User) = parse_update(update)
        debug_logger.log(f"help => message={message}")
        debug_logger.log(f"help => user={user}")
        username: str = try_get(user, "username")
        debug_logger.log(f"help => /help executed by {username}")
        return await update.message.reply_text("help_menu_message")
    except Exception as exception:
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"help => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        raise exception


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        debug_logger.log(f"start => Raw update={update}")
        success, message, chat, user = parse_update(update)
        if not success:
            raise Exception(f"parse_update: message={message} chat={chat} user={user}")
        debug_logger.log(f"start => message={message}")
        debug_logger.log(f"start => chat={chat}")
        debug_logger.log(f"start => user={user}")

        success, message_text, chat_id, user_id = parse_update_data(message, chat, user)
        if not success:
            raise Exception(
                f"parse_update: message={message}" f"chat={chat}" f"user={user}"
            )
        debug_logger.log(f"start => message_text={message_text}")
        debug_logger.log(f"start => chat_id={chat_id}")
        debug_logger.log(f"start => user_id={user_id}")

        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in admins]
        if user_id not in admin_ids:
            return await update.message.reply_text(
                "Sorry, you are not an admin! Please ask an admin to run the /start command."
            )

        started = abbit.start()
        if not started:
            raise Exception(f"Not started! started={started}")

        abbit.update_chat_history(dict(role="user", content=message_text))
        await message.reply_text(
            f"Please wait while we unplug {BOT_NAME} from the Matrix"
        )

        response = abbit.chat_history_completion()
        if not response:
            error_msg = f"Please try again later or contact @nonni_io"
            started = abbit.stop()
            response = f"{abbit.name} failed to start ⛔️! {error_msg}."
            return await context.bot.send_message(
                chat_id=THE_CREATOR, text=f"response={response}"
            )
        await message.reply_text(response)
    except Exception as exception:
        error_logger.log(f"start => Raw exception={exception}")
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"start => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        raise exception


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        debug_logger.log(f"stop => Raw update={update}")
        success, message, chat, user = parse_update(update)
        if not success:
            raise Exception(f"parse_update: message={message} chat={chat} user={user}")
        debug_logger.log(f"start => message={message}")
        debug_logger.log(f"start => chat={chat}")
        debug_logger.log(f"start => user={user}")

        success, message_text, chat_id, user_id = parse_update_data(message, chat, user)
        if not success:
            raise Exception(
                f"parse_update: message={message}" f"chat={chat}" f"user={user}"
            )
        debug_logger.log(f"start => message_text={message_text}")
        debug_logger.log(f"start => chat_id={chat_id}")
        debug_logger.log(f"start => user_id={user_id}")

        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in admins]
        if user_id not in admin_ids:
            return await update.message.reply_text(
                "Sorry, you are not an admin! Please ask an admin to run the /start command."
            )
        started, _ = abbit.status()
        if not started:
            debug_logger.log(f"stop => Not started! abbit.started={abbit.started}")
            return await message.reply_text(
                f"/stop failed! No Abbot to stop! Have you run /start yet?"
                "If so, please try again later or contact @nonni_io"
            )

        stopped = abbit.stop()
        if not stopped:
            err_msg = f"stop => not stopped! abbit={abbit}, running={stopped}"
            error_logger.log(err_msg)
            await message.reply_text(
                "/stop failed! Something went wrong. Please try again later or contact @nonni_io"
            )
            return await context.bot.send_message(chat_id=THE_CREATOR, text=err_msg)

        await message.reply_text(
            f"Thanks for using {BOT_NAME}. To restart, have an admin run the /start command."
        )
    except Exception as exception:
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_logger.log(f"stop => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        raise exception
