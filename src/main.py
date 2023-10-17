from sys import argv

import re
import json
import time
from io import open
from os import listdir
from os.path import abspath

from random import randrange
from help_menu import help_menu_message
from uuid import uuid4
from datetime import datetime, timedelta

from telegram import Update, Message, Chat, User
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)

from lib.utils import (
    try_get,
    try_gets,
    try_set,
    qr_code,
)
from lib.logger import debug, error
from lib.creator.admin_service import AdminService
from lib.api.strike import Strike
from lib.gpt import GPT, Abbots

from bot_env import BOT_TOKEN, TEST_BOT_TOKEN, STRIKE_API_KEY
from bot_constants import (
    BOT_NAME,
    BOT_HANDLE,
    COUNT,
    INIT_GROUP_MESSAGE,
    INIT_PRIVATE_MESSAGE,
    THE_CREATOR,
    ATL_BITCOINER,
    CHAT_TITLE_TO_SHORT_TITLE,
    SUPER_DOOPER_ADMINS,
    CHEEKY_RESPONSES,
)

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MESSAGES_JL_FILE = abspath("src/data/messages.jsonl")
SUMMARY_LOG_FILE = abspath("src/data/backup/summaries.txt")
MESSAGES_PY_FILE = abspath("src/data/backup/messages.py")
PROMPTS_BY_DAY_FILE = abspath("src/data/backup/prompts_by_day.py")
now = datetime.now()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        if not message:
            debug(f"handle_message => Missing Message: {message}")
            return
        if not chat:
            debug(f"handle_message => Missing Chat: {chat}")
            return
        debug(f"handle_message => Message={message}")
        debug(f"handle_message => Chat={chat}")
        username = try_get(message, "from_user", "username")
        date = (try_get(message, "date") or now).strftime("%m/%d/%Y")
        name = try_get(chat, "first_name", default=username)
        chat_id = try_get(chat, "id")
        chat_type = try_get(chat, "type")
        message_text = try_get(message, "text")
        if not message_text:
            debug(f"handle_message => Missing message text={message_text}")
            return
        debug(f"handle_message => Message text={message_text}")
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        bot_context = "group"
        if is_group_chat or not is_private_chat:
            if BOT_HANDLE != "test_atl_bitlab_bot":
                chat_title: str = try_get(chat, "title", default="").lower().replace(" ", "")
                debug(f"handle_message => not is_private_chat={not is_private_chat}")
                debug(f"handle_message => is_group_chat={is_group_chat}")
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
                debug(f"handle_message => message_dump={message_dump}")
                raw_messages_jsonl = open(RAW_MESSAGE_JL_FILE, "a")
                raw_messages_jsonl.write(message_dump)
                raw_messages_jsonl.write("\n")
                raw_messages_jsonl.close()
        else:
            bot_context = "private"
            debug(f"handle_message => is_private_chat={is_private_chat}")
        debug(f"handle_message => bot_context={bot_context}")

        which_abbot: GPT = try_get(ABBOTS, chat_id)
        if not which_abbot:
            which_bot_name = f"{bot_context}{BOT_NAME}{chat_id}"
            which_abbot = GPT(
                which_bot_name, BOT_HANDLE, ATL_BITCOINER, bot_context, chat_id
            )

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
                debug(f"handle_message => Abbot not started")
                debug(f"which_abbot={which_abbot.__str__()}")
                intro_sent = which_abbot.introduce()
                debug(f"intro_sent={intro_sent}")
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
            debug(f"handle_message => group_in_name")
            debug(f"handle_message => which_name={which_name}")
            if full_handle not in message_text:
                return
            if not reply_to_which_abbot:
                return
            if full_handle not in reply_to_message_text:
                return
            if is_modulo_message:
                return
            debug(f"handle_message => All checks passed!")
            answer = which_abbot.chat_history_completion()
        else:
            debug(f"handle_message => is private, not group_in_name")
            answer = which_abbot.chat_history_completion()

        if not answer:
            if which_abbot.sleep(10):
                await message.reply_text(
                    "Sorry, I was taking a quick nap 😴." "Still a lil groggy 🥴."
                )
            debug(f"handle_message => which_abbot={which_abbot}")
            return await context.bot.send_message(
                chat_id=THE_CREATOR,
                text=f"{which_abbot.name} completion failed ⛔️: which_abbot={which_abbot} answer={answer}",
            )
        return await message.reply_text(answer)

    except Exception as exception:
        debug(f"handle_message => Error={exception}")
        debug(f"handle_message => which_abbot={which_abbot}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )


def clean_data():
    try:
        debug(f"clean_data => Deduping messages")
        seen = set()
        raw_open = open(RAW_MESSAGE_JL_FILE, "r")
        messages_open = open(MESSAGES_JL_FILE, "w")
        with raw_open as infile, messages_open as outfile:
            for line in infile:
                obj_hash = hash(json.dumps(obj, sort_keys=True))
                debug(f"clean_data => line={line}")
                try:
                    obj = json.loads(obj)
                except Exception as exception:
                    exception_msg = (
                        f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
                    )
                    debug(
                        f"clean_data => Exception={exception}, ExceptionMessage={exception_msg}"
                    )
                    continue
                if obj_hash not in seen:
                    seen.add(obj_hash)
                    # get and clean text
                    obj_text = try_get(obj, "text")
                    apos_in_text = "'" in obj_text
                    obj_title = try_get(obj, "title")
                    title_has_spaces = " " in obj_title
                    obj_date = try_get(obj, "date")
                    plus_in_date = "+" in obj_date
                    t_in_date = "T" in obj_date
                    plus_and_t = plus_in_date and t_in_date
                    if not obj_text:
                        continue
                    elif apos_in_text:
                        obj = try_set(obj, obj_text.replace("'", ""), "text")
                    if not obj_title:
                        continue
                    elif title_has_spaces:
                        clean_title = try_get(
                            CHAT_TITLE_TO_SHORT_TITLE,
                            obj_title,
                            default=obj_title.lower().replace(" ", ""),
                        )
                        obj = try_set(obj, clean_title, "title")
                    if not obj_date:
                        continue
                    elif plus_and_t:
                        obj = try_set(
                            obj,
                            obj_date.replace("+", " ").replace("T", " ").split(" ")[0],
                            "date",
                        )
                    elif plus_in_date:
                        obj = try_set(
                            obj, obj_date.replace("+", " ").split(" ")[0], "date"
                        )
                    elif t_in_date:
                        obj = try_set(
                            obj, obj_date.replace("T", " ").split(" ")[0], "date"
                        )

                    outfile.write(json.dumps(obj))
                    outfile.write("\n")
        infile.close()
        outfile.close()
        debug(f"clean_data => Deduping done")
        return True
    except Exception as exception:
        raise exception

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        sender = try_get(message, "from_user", "username")
        message_text = try_get(message, "text")
        chat: Chat = try_get(update, "effective_chat") or try_get(message, "chat")
        chat_type = try_get(chat, "type")
        private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        debug(f"help => /help executed by {sender}")
        if is_group_chat:
            if f"@{BOT_HANDLE}" not in message_text:
                return await message.reply_text(
                    f"For help, tag @{BOT_HANDLE} in the help command: e.g. /help @{BOT_HANDLE}",
                )
            return await message.reply_text(help_menu_message)
        if private_chat:
            await message.reply_text(help_menu_message)
    except Exception as exception:
        error(f"help => Error={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )
        raise exception


async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message: Message = try_get(update, "message")
        message_text = try_get(message, "text")
        chat = try_get(update, "effective_chat") or try_get(message, "chat")
        if not message or not chat:
            raise Exception(f"Error: unleash: message={message} or chat={chat} missing")
        chat_type = try_get(chat, "type")
        private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        chat_id = try_get(chat, "id")
        sender = try_get(message, "from_user", "username")
        debug(f"unleash => /unleash {args} executed by {sender}")
        if sender not in SUPER_DOOPER_ADMINS:
            cheek = CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))]
            return await message.reply_text(cheek)
        if f"@{BOT_HANDLE}" not in message_text:
            return await message.reply_text(
                (
                    f"To unleash @{BOT_HANDLE}, run unleash with proper args from proper context"
                    f"(within private message or group chat): e.g. to unleash: /unleash 1 @{BOT_HANDLE}"
                )
            )
        UNLEASH = ("1", "True", "On")
        LEASH = ("0", "False", "Off")
        UNLEASH_LEASH = (*UNLEASH, *LEASH)
        bot_status = try_get(args, 0, default="False").capitalize()
        debug(f"unleash => bot_status={bot_status}")
        if bot_status not in UNLEASH_LEASH:
            return await message.reply_text(
                f"Bad arg: expecting one of {UNLEASH_LEASH}"
            )
        if private_chat:
            bot_context = "private"
        elif is_group_chat:
            bot_context = "group"
        debug(f"unleash => bot_context={bot_context}")
        which_abbot = try_get(ABBOTS, chat_id)
        if not which_abbot:
            bot_name = (
                f"{bot_context}{BOT_NAME}-{chat_id}"
                if bot_context == "private"
                else f"{bot_context}{BOT_NAME}{chat_id}",
            )
            which_abbot = GPT(
                bot_name,
                BOT_HANDLE,
                ATL_BITCOINER,
                bot_context,
                chat_id,
                True,
            )
            debug(f"unleash => abbot={which_abbot}")
        if bot_status in UNLEASH:
            unleashed = which_abbot.unleash()
        else:
            unleashed = which_abbot.leash()

        which_abbot.update_abbots(chat_id, which_abbot)
        response = "unleashed ✅" if unleashed else "leashed ⛔️"
        which_abbot_name = which_abbot.name
        debug(f"unleash => {which_abbot_name} {response}")
        return await message.reply_text(f"{which_abbot_name} {response}")
    except Exception as exception:
        error(f"statuses => Error={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )
        raise exception


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        chat = try_get(update, "effective_chat") or try_get(message, "chat")
        chat_id = try_get(chat, "id")
        sender = try_get(message, "from_user", "username")
        debug(
            f"rules => /rules executed by {sender} - chat={chat} chat_id={chat_id}"
        )
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
        error(f"statuses => Error={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )
        raise exception


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        debug(f"start => Raw update={update}")
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        user: User = try_get(message, "from_user")
        if not message:
            debug(f"start => Missing Message: {message}")
            return
        if not chat:
            error(f"start => Missing Chat: {chat}")
            return
        if not user:
            error(f"start => Missing User: {user}")
            return
        debug(f"start => Message={message}")
        debug(f"start => Chat={chat}")
        debug(f"start => User={user}")
        message_text = try_get(message, "text")
        chat_id = try_get(chat, "id")
        chat_type = try_get(chat, "type")
        user_id = try_get(user, "id")
        if not message_text:
            debug(f"start => Missing Message Text: {message_text}")
            return
        if not chat_id:
            error(f"start => Missing Chat ID: {chat_id}")
            return
        if not chat_type:
            error(f"start => Missing Chat Type: {chat_type}")
            return
        if not user_id:
            debug(f"start => Missing User ID: {user_id}")
            return
        debug(f"start => message_text={message_text}")
        debug(f"start => chat_id={chat_id}")
        debug(f"start => chat_type={chat_type}")
        debug(f"start => user_id={user_id}")
        private_chat = chat_type == "private"
        if not private_chat:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id not in admin_ids:
                return await update.message.reply_text(
                    "Sorry, you are not an admin! Please ask an admin to run the /start command."
                )
        bot_context = "group"
        creator_content = INIT_GROUP_MESSAGE
        if private_chat:
            debug(f"start => private_chat={private_chat}")
            bot_context = "private"
            creator_content = INIT_PRIVATE_MESSAGE
        debug(f"start => bot_context={bot_context}")
        debug(f"start => creator_content={creator_content}")
        which_abbot = try_get(ABBOTS, chat_id)
        if not which_abbot:
            which_bot_name = f"{bot_context}{BOT_NAME}{chat_id}"
            which_abbot = GPT(
                which_bot_name,
                BOT_HANDLE,
                ATL_BITCOINER,
                bot_context,
                chat_id,
                True,
            )
        if not which_abbot:
            debug(f"start => No abbot! Which Abbot: {which_abbot}")
            return await message.reply_text(
                f"/start failed ... please try again later or contact @nonni_io"
            )
        which_name = which_abbot.name
        which_handle = which_abbot.handle
        which_history_len = len(which_abbot.chat_history)
        debug(f"start => which_name={which_name}")
        debug(f"start => which_handle={which_handle}")
        debug(f"start => which_history_len={which_history_len}")
        started = which_abbot.start()
        if not started:
            raise Exception(f"Not started! started={started}")
        which_abbot.update_chat_history(dict(role="user", content=message_text))
        which_abbot.update_abbots(chat_id, which_abbot)
        error_msg = f"Please try again later or contact @nonni_io"
        await message.reply_text(
            f"Please wait while we unplug {BOT_NAME} from the Matrix"
        )
        response = which_abbot.chat_history_completion()
        if not response:
            status = which_abbot.leash()
            response = f"{which_abbot.name} leashed={status} ⛔️! {error_msg}."
            return await context.bot.send_message(
                chat_id=THE_CREATOR, text=f"status={status} response={response}"
            )
        await message.reply_text(response)
    except Exception as exception:
        error(f"start => Raw exception={exception}")
        error(f"start => Error={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )
        raise exception


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        debug(f"stop => Raw update={update}")
        message: Message = try_get(update, "message") or try_get(
            update, "effective_message"
        )
        chat: Chat = try_get(message, "chat") or try_get(update, "effective_chat")
        user: User = try_get(message, "from_user")
        if not message:
            debug(f"stop => Missing Message: {message}")
            return
        if not chat:
            error(f"stop => Missing Chat: {chat}")
            return
        if not user:
            error(f"stop => Missing User: {user}")
            return
        debug(f"stop => Message={message}")
        debug(f"stop => Chat={chat}")
        debug(f"stop => User={user}")
        message_text = try_get(message, "text")
        chat_id = try_get(chat, "id")
        chat_type = try_get(chat, "type")
        user_id = try_get(user, "id")
        if not message_text:
            debug(f"stop => Missing Message Text: {message_text}")
            return
        if not chat_id:
            error(f"stop => Missing Chat ID: {chat_id}")
            return
        if not chat_type:
            error(f"stop => Missing Chat Type: {chat_type}")
            return
        if not user_id:
            debug(f"stop => Missing User ID: {user_id}")
            return
        debug(f"stop => message_text={message_text}")
        debug(f"stop => chat_id={chat_id}")
        debug(f"stop => chat_type={chat_type}")
        debug(f"stop => user_id={user_id}")
        private_chat = chat_type == "private"
        if not private_chat:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id not in admin_ids:
                return await update.message.reply_text(
                    "Sorry, you are not an admin! Please ask an admin to run the /stop command."
                )
        debug(f"stop => /stop executed by {user} in group chat {chat_id}")
        which_abbot: GPT = try_get(ABBOTS, chat_id)
        debug(f"stop => which_abbot={which_abbot}")

        if not which_abbot:
            debug(f"stop => No abbot! which_abbot={which_abbot}")
            return await message.reply_text(
                f"/stop failed! No Abbot to stop! Have you run /start yet?"
                "If so, please try again later or contact @nonni_io"
            )
        if not which_abbot.started:
            debug(f"stop => Not started! which_abbot.started={which_abbot.started}")
            return await message.reply_text(
                f"/stop failed! No Abbot to stop! Have you run /start yet?"
                "If so, please try again later or contact @nonni_io"
            )
        running = which_abbot.stop()
        if running:
            err_msg = (
                f"stop => not stopped! which_abbot={which_abbot}, running={running}"
            )
            error(err_msg)
            await message.reply_text(
                "/stop failed! Something went wrong. Please try again later or contact @nonni_io"
            )
            return await context.bot.send_message(chat_id=THE_CREATOR, text=err_msg)
        await message.reply_text(
            f"Thanks for using {BOT_NAME}. Use /start to restart at any time."
        )
    except Exception as exception:
        error(f"stop => Error={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception}"
        )
        raise exception


async def _admin_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "_admin_plugin:"
        chat_id: int = try_get(update, "message", "chat", "id")
        user_id: int = try_get(update, "message", "from_user", "id")
        if user_id != THE_CREATOR:
            return
        admin: AdminService = AdminService(user_id, chat_id)
        admin.stop_service()
    except Exception as exception:
        error(f"{fn} => exception={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{fn} exception: {exception}"
        )
        raise exception


async def _admin_unplug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "_admin_unplug:"
        chat_id: int = try_get(update, "message", "chat", "id")
        user_id: int = try_get(update, "message", "from_user", "id")

        admin: AdminService = AdminService(user_id, chat_id)
        admin.start_service()
    except Exception as exception:
        error(f"{fn} => exception={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{fn} exception: {exception}"
        )
        raise exception


async def _admin_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "_admin_kill:"
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
        error(f"{fn} => exception={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{fn} exception: {exception}"
        )
        raise exception


async def _admin_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fn = "_admin_nap:"
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
        error(f"{fn} => exception={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{fn} exception: {exception}"
        )
        raise exception


async def _admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE, abbots: Abbots):
    try:
        fn = "status:"
        message: Message = try_get(update, "message")
        user: User = try_get(message, "from_user")
        user_id: int = try_get(user, "id")
        if user_id != THE_CREATOR:
            return
        abbots_dict: dict = abbots.get_bots()
        for bot in abbots_dict:
            abbot: GPT = bot
            status_data = json.dumps(abbot.get_status(), indent=4)
            debug(f"statuses => {abbot.name} status_data={status_data}")
            await message.reply_text(status_data)
    except Exception as exception:
        error(f"{fn} => exception={exception}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{fn} exception: {exception}"
        )
        raise exception

ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
DEV_MODE = "-d" in ARGS or "--dev" in ARGS
CLEAN_SUMMARY = CLEAN and SUMMARY

TOKEN = TEST_BOT_TOKEN if DEV_MODE else BOT_TOKEN
APPLICATION = ApplicationBuilder().token(TOKEN).build()
debug(f"{BOT_NAME} @{BOT_HANDLE} Initialized")

BOT_NAME = f"t{BOT_NAME}" if DEV_MODE else BOT_NAME
BOT_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE
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
    bot_context = "group"
    chat_id = int(content.split(".")[0])
    abbot_name = f"{bot_context}{BOT_NAME}{chat_id}"
    config_json = json.load(open(f"{GROUP_CONFIG_FILE_PATH}/{config}", "r"))
    debug(f"main => chat_id={chat_id} abbot_name={abbot_name}")
    group_abbot = GPT(
        abbot_name,
        BOT_HANDLE,
        ATL_BITCOINER,
        bot_context,
        chat_id,
        bool(try_get(config_json, "consent")),
    )
    ALL_ABBOTS.append(group_abbot)

for content, config in zip(PRIVATE_CONTENT_FILES, PRIVATE_CONFIG_FILES):
    if ".jsonl" not in content or ".json" not in config:
        continue
    bot_context = "private"
    chat_id = int(content.split(".")[0])
    abbot_name = f"{bot_context}{BOT_NAME}{chat_id}"
    config_json = json.load(open(f"{PRIVATE_CONFIG_FILE_PATH}/{config}", "r"))
    group_abbot = GPT(
        abbot_name,
        BOT_HANDLE,
        ATL_BITCOINER,
        bot_context,
        chat_id,
        bool(try_get(config_json, "consent")),
    )
    ALL_ABBOTS.append(group_abbot)

abbots = Abbots(ALL_ABBOTS)
ABBOTS: Abbots.BOTS = abbots.get_bots()
debug(f"main abbots => {abbots.__str__()}")

kill_handler = CommandHandler("unplug", _admin_unplug)
revive_handler = CommandHandler("plugin", _admin_plugin)
help_handler = CommandHandler("nap", _admin_nap)
status_handler = CommandHandler("status", _admin_status(abbots))


help_handler = CommandHandler("help", help)
rules_handler = CommandHandler("rules", rules)
start_handler = CommandHandler("start", start)
stop_handler = CommandHandler("stop", stop)
unleash_handler = CommandHandler("unleash", unleash)
message_handler = MessageHandler(BaseFilter(), handle_message)

APPLICATION.add_handler(kill_handler)
APPLICATION.add_handler(revive_handler)
APPLICATION.add_handler(help_handler)
APPLICATION.add_handler(stop_handler)
APPLICATION.add_handler(unleash_handler)
APPLICATION.add_handler(status_handler)
APPLICATION.add_handler(rules_handler)
APPLICATION.add_handler(start_handler)
APPLICATION.add_handler(message_handler)

debug(f"{BOT_NAME} @{BOT_HANDLE} Polling")
admin = AdminService(THE_CREATOR, THE_CREATOR)
admin.status = "running"
APPLICATION.run_polling()
