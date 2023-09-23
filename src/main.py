from functools import wraps
from sys import argv

ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
DEV_MODE = "-d" in ARGS or "--dev" in ARGS
CLEAN_SUMMARY = CLEAN and SUMMARY

from constants import (
    BOT_NAME,
    BOT_HANDLE,
    SUMMARY_ASSISTANT,
    PROMPT_ASSISTANT,
    THE_CREATOR,
    ATL_BITCOINER,
)

BOT_NAME = f"t{BOT_NAME}" if DEV_MODE else BOT_NAME
BOT_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE

import json
import time
import re
from io import open
from os.path import abspath

from random import randrange
from help_menu import help_menu_message
from uuid import uuid4
from datetime import datetime
from lib.utils import (
    get_dates,
    try_get,
    try_get_telegram_message_data,
    try_gets,
    try_set,
    qr_code,
)

from lib.logger import debug, error

from telegram import Update, Message
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)

from lib.api.strike import Strike
from lib.gpt import GPT, Abbots

PROMPT_ABBOT = GPT(BOT_NAME, BOT_HANDLE, PROMPT_ASSISTANT, "prompt")
SUMMARY_ABBOT = GPT(f"s{BOT_NAME}", BOT_HANDLE, SUMMARY_ASSISTANT, "summary")
ABBOTS = Abbots(PROMPT_ABBOT, SUMMARY_ABBOT)

from env import BOT_TOKEN, TEST_BOT_TOKEN, STRIKE_API_KEY

BOT_DATA = open(abspath("data/bot_data.json"), "r")
BOT_DATA_OBJ = json.load(BOT_DATA)
CHATS_TO_IGNORE = try_get(BOT_DATA_OBJ, "chats", "ignore")
CHATS_TO_INCLUDE_SUMMARY = try_get(BOT_DATA_OBJ, "chats", "include", "summary")
CHAT_NAME_MAPPING = try_get(BOT_DATA_OBJ, "chats", "mapping", "nameToShortName")
WHITELIST = try_get(BOT_DATA_OBJ, "whitelist")
CHEEKY_RESPONSES = try_get(BOT_DATA_OBJ, "responses", "cheeky")
PITHY_RESPONSES = try_get(BOT_DATA_OBJ, "responses", "pithy")
RAW_MESSAGE_JL_FILE = abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = abspath("data/summaries.txt")
MESSAGES_PY_FILE = abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = abspath("data/backup/prompts_by_day.py")
now = datetime.now()
now_iso = now.isoformat()
now_iso_clean = now_iso.split("+")[0].split("T")[0]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"handle_message => Raw update={update}")
    mpy = open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()

    message = (
        try_get(update, "message")
        or try_get(update, "effective_message")
        or update.message
    )
    if not message:
        debug(f"handle_message => Missing Message object={message}")
        return
    debug(f"handle_message => Raw message={message}")

    reply_to_message = try_get(message, "reply_to_message")
    debug(f"handle_message => reply_to_message={reply_to_message}")
    reply_to_message_from = try_get(reply_to_message, "from")
    reply_to_message_from_bot = try_get(reply_to_message_from, "is_bot")
    reply_to_message_bot_username = try_get(reply_to_message_from, "username")

    all_message_data = try_get_telegram_message_data(message)
    debug(f"handle_message => all_message_data={all_message_data}")

    chat = try_get(update, "effective_chat") or try_get(message, "chat")
    debug(f"handle_message => Raw chat={chat}")

    message_text = try_get(message, "text")
    debug(f"handle_message => Message text={message_text}")
    if not message_text:
        debug(f"handle_message => Missing message text={message_text}")
        return

    username = try_get(message, "from_user", "username")
    date = (try_get(message, "date") or now).isoformat().split("+")[0].split("T")[0]
    name = try_get(chat, "first_name", default=username)
    chat_id = try_get(chat, "id")
    chat_type = try_get(chat, "type")
    is_private_chat = chat_type == "private"
    is_chat_to_ignore = chat_id in CHATS_TO_IGNORE
    default = "private" if is_private_chat else ""
    chat_title = try_get(chat, "title", default)

    if not is_private_chat and not is_chat_to_ignore:
        debug(f"handle_message => is_private_chat={is_private_chat}")
        debug(f"handle_message => is_chat_to_ignore={is_chat_to_ignore}")
        chat_title = try_get(CHAT_NAME_MAPPING, chat_title, default="atlantabitdevs")
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
        rm_jl = open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dump)
        rm_jl.write("\n")
        rm_jl.close()

    which_abbot = None
    is_group_chat = not is_private_chat and chat_id not in CHATS_TO_INCLUDE_SUMMARY
    if is_group_chat:
        bot_context = "group"
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
        debug(f"handle_message => is_group_chat={is_group_chat}, bot={which_abbot}")
    elif is_private_chat:
        bot_context = "private"
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
        debug(f"handle_message => is_private_chat={is_private_chat}, bot={which_abbot}")
    debug(f"handle_message => ABBOTS={ABBOTS}")
    if not which_abbot:
        debug(f"handle_message => No abbot! which_abbot={which_abbot}")
        return
    which_name = which_abbot.name
    which_handle = which_abbot.handle
    which_history_len = len(which_abbot.chat_history)
    which_abbot.update_chat_history(dict(role="user", content=message_text))
    which_abbot.update_abbots(chat_id, which_abbot)
    got_abbots = which_abbot.get_abbots()
    chat_history = which_abbot.get_chat_history()
    debug(f"handle_message => got_abbots={got_abbots} chat_history={chat_history}")
    if "group" in which_name:
        if not reply_to_message:
            msg = f"handle_message => which_name={which_name}, reply_to_message={reply_to_message}"
            debug(msg)
            if f"@{which_handle}" not in message_text and which_history_len % 5 != 0:
                msg = f"handle_message => {which_handle} not tagged, message_text={message_text}"
                debug(msg)
                debug(f"handle_message => len % 5 != 0, len={which_history_len}")
                return
        elif not reply_to_message_from_bot:
            msg = f"handle_message => reply_to_message_from_bot={reply_to_message_from_bot}"
            debug(msg)
            debug(f"handle_message => reply_to_message={reply_to_message}")
            return
        elif reply_to_message_bot_username != which_handle:
            msg = f"handle_message => bot_username != which_handle={reply_to_message_bot_username != which_handle}"
            debug(msg)
            debug(f"handle_message => bot_username={reply_to_message_bot_username}")
            debug(f"handle_message => which_handle={which_handle}")
            return

    debug(f"handle_message => All checks passed!")
    error = f"Please try again later. {which_abbot.name} leashed ⛔️"
    answer = which_abbot.chat_completion()
    response = error if not answer else answer
    return await message.reply_text(response)


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
                    cause, traceback, args = deconstruct_error(exception)
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
                            CHAT_NAME_MAPPING,
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


def rand_num():
    return randrange(len(CHEEKY_RESPONSES))


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE, both: bool = False):
    try:
        message = (
            try_get(update, "message")
            or try_get(update, "effective_message")
            or update.message
        )
        sender = try_get(message, "from_user", "username")
        debug(f"clean => /clean executed by {sender}")
        if not message or not sender:
            debug(f"clean => message={message} sender={sender} undefined")
            return await message.reply_text()
        elif sender not in WHITELIST:
            debug(f"clean => sender={sender} not whitelisted")
            return await message.reply_text(CHEEKY_RESPONSES[rand_num()])
        return clean_data()
    except Exception as exception:
        if not both:
            cause, traceback, args = deconstruct_error(exception)
            error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}\n"
            debug(f"clean => Error={exception}, ErrorMessage={error_msg}")
            await context.bot.send_message(
                chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
            )
            await message.reply_text(f"Sorry ... taking a nap. Hmu later.")
        raise exception


async def both(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = (
            try_get(update, "message")
            or try_get(update, "effective_message")
            or update.message
        )
        await message.reply_text("Cleaning ... please wait")
        await clean(update, context, both=True)
        await message.reply_text("Cleaning done!")
        await message.reply_text("Generating summaries ... please wait")
        await summary(update, context, both=True)

    except Exception as exception:
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        debug(f"both => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        await message.reply_text(f"Sorry ... taking a nap. Hmu later.")


def whitelist_gate(sender):
    return sender not in WHITELIST


def summarize_messages(chat, days=None):
    try:
        summaries = []
        prompts_by_day = {k: "" for k in days}
        for day in days:
            prompt_content = ""
            messages_file = open(RAW_MESSAGE_JL_FILE, "r")
            for line in messages_file.readlines():
                message = json.loads(line)
                message_date = try_get(message, "date")
                message_title = try_get(message, "title")
                if day == message_date and chat == message_title:
                    text = try_get(message, "text")
                    sender = try_get(message, "from")
                    message = f"{sender} said {text} on {message_date}\n"
                    prompt_content += message
            if prompt_content == "":
                continue
            prompts_by_day[day] = prompt_content
        messages_file.close()
        prompts_by_day_file = open(PROMPTS_BY_DAY_FILE, "w")
        prompts_by_day_dump = json.dumps(prompts_by_day)
        prompts_by_day_file.write(prompts_by_day_dump)
        prompts_by_day_file.close()
        debug(f"summarize_messages => Prompts by day = {prompts_by_day_dump}")
        summary_file = open(SUMMARY_LOG_FILE, "a")
        prompt = "Summarize the text after the asterisk. Split into paragraphs where appropriate. Do not mention the asterisk. * \n"
        for day, content in prompts_by_day.items():
            SUMMARY_ABBOT.update_chat_history(f"{prompt}{content}")
            SUMMARY_ABBOT.update_abbots("prompt", SUMMARY_ABBOT)
        answer = SUMMARY_ABBOT.chat_completion()
        debug(f"summarize_messages => OpenAI Response = {answer}")
        summary = f"Summary {day}:\n{answer.strip()}"
        summary_file.write(f"{summary}\n--------------------------------\n\n")
        summaries.append(summary)
        summary_file.close()
        return summaries
    except Exception as exception:
        debug(f"summarize_messages => error: {exception}")
        raise exception


async def summary(
    update: Update, context: ContextTypes.DEFAULT_TYPE, both: bool = False
):
    try:
        message = update.effective_message
        sender = message.from_user.username
        debug(f"summary => /summary executed by {sender}")
        if whitelist_gate(sender):
            return await message.reply_text(
                CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        args = try_get(context, "args")
        arg_len = len(args)
        if arg_len > 3:
            return await message.reply_text("Bad args: too many args")
        date_regex = "^\d{4}-\d{2}-\d{2}$"
        dates = get_dates()
        chat = try_get(args, 0).replace(" ", "").lower()
        if chat != "atlantabitdevs":
            return await message.reply_text("Bad args: Expecting 'atlantabitdevs'")
        response_message = f"Generating {chat} summary for {dates}"
        if arg_len == 2:
            date = try_get(args, 1)
            if not re.search(date_regex, date):
                error = f"Bad args: for 2 args, expecting '/command <chatname> <date>', received {''.join(args)}; e.g. /summary atlantabitdevs 2023-01-01"
                return await message.reply_text(error)
            dates = [date]
            response_message = f"Generating {chat} summary for {dates}"
        elif arg_len == 3:
            dates = try_get(args[1:])
            response_message = f"Generating {chat} summary for {dates}"
            for date in dates:
                if not re.search(date_regex, date):
                    error = f"Bad args: expecting '/summary <chatname> <date> <date>', received {''.join(args)}; e.g. /summary atlantabitdevs 2023-01-01 2023-01-03"
                    return await message.reply_text(error)
        else:
            response_message = f"Generating {chat} summary for {dates}"
        await message.reply_text(response_message)
        await message.reply_text(summarize_messages(chat, dates))
        return True
    except Exception as exception:
        if not both:
            cause, traceback, args = deconstruct_error(exception)
            error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
            debug(f"summary => Error={exception}, ErrorMessage={error_msg}")
            await context.bot.send_message(
                chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
            )
            await message.reply_text(f"Sorry ... taking a nap. Hmu later.")
        raise exception


async def abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        message = update.effective_message
        debug(f"abbot => /prompt executed => sender={sender} message={message}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Working on your request"
        )
        args = context.args
        debug(f"abbot => args: {args}")
        if len(args) <= 0:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error: You didn't provide a prompt",
            )
        prompt = " ".join(args)
        strike = Strike(
            STRIKE_API_KEY,
            str(uuid4()),
            f"ATL BitLab Bot: Payer => {sender}, Prompt => {prompt}",
        )
        invoice, expiration = strike.invoice()
        qr = qr_code(invoice)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=qr,
            caption=f"Please pay the invoice to get the answer to the question:\n{prompt}",
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"`{invoice}`",
            parse_mode="MarkdownV2",
        )
        while not strike.paid():
            if expiration == 0:
                strike.expire_invoice()
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expired. Retry?",
                )
            if expiration % 10 == 7:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expires in {expiration} seconds",
                )
            expiration -= 1
            time.sleep(1)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Thank you for supporting ATL BitLab!",
        )
        PROMPT_ABBOT.update_message_content(prompt)
        answer = PROMPT_ABBOT.chat_completion()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"{answer}"
        )
        debug(f"abbot => Answer: {answer}")
    except Exception as error:
        debug(f"abbot => /prompt Error: {error}")
        await message.reply_text(f"Error: {error}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    message = update.effective_message
    message_text = message.text
    debug(f"stop => /stop executed by {sender}")
    if sender not in WHITELIST:
        return await message.reply_text(
            CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
        )
    if f"@{BOT_HANDLE}" not in message_text:
        return await message.reply_text(
            f"To stop, tag @{BOT_HANDLE} in the help command: e.g. /stop @{BOT_HANDLE}"
        )

    await context.bot.stop_poll(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.id,
        text=f"@{BOT_HANDLE} stopped! Use /start @{BOT_HANDLE} to restart bot",
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        try_get(update, "message")
        or try_get(update, "effective_message")
        or update.message
    )
    message_text = try_get(message, "text")
    debug(f"help => /help executed by {update.effective_message.from_user.username}")
    if f"@{BOT_HANDLE}" not in message_text:
        return await message.reply_text(
            chat_id=update.effective_chat.id,
            text=f"For help, tag @{BOT_HANDLE} in the help command: e.g. /help @{BOT_HANDLE}",
        )
    await message.reply_text(
        chat_id=update.effective_chat.id,
        text=help_menu_message,
    )


def trycatch(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # ---- Success ----
            return fn(*args, **kwargs)
        except Exception as error:
            debug(f"abbot => /prompt Error: {error}")
            raise error

    return wrapper


def deconstruct_error(error):
    return try_gets(error, keys=["__cause__", "__traceback__", "args"])


async def abbot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = (
            try_get(update, "message")
            or try_get(update, "effective_message")
            or update.message
        )
        chat = try_get(update, "effective_chat") or try_get(message, "chat")
        chat_type = try_get(chat, "type")
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        chat_id = try_get(chat, "id")
        sender = try_get(message, "from_user", "username")
        debug(f"abbot_status => /status executed by {sender}")

        if sender not in WHITELIST:
            cheek = CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))]
            return await message.reply_text(cheek)

        if is_private_chat:
            bot_context = "private"
        elif is_group_chat:
            bot_context = "group"
        debug(f"abbot_status => bot_context={bot_context}")
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
            which_abbot.update_abbots(chat_id, which_abbot)
            debug(f"abbot_status => bot={which_abbot}")
        got_abbots = which_abbot.get_abbots()
        for _, abbot in got_abbots.items():
            status = json.dumps(abbot.status(), indent=4)
            debug(f"abbot_status => {abbot.name} status={status}")
            await message.reply_text(status)
    except Exception as exception:
        exception.with_traceback(None)
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        debug(f"abbot_status => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        await message.reply_text(f"Sorry ... taking a nap. Hmu later.")
        raise exception


async def unleash_the_abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = try_get(context, "args")
        message = (
            try_get(update, "message")
            or try_get(update, "effective_message")
            or update.message
        )
        message_text = try_get(message, "text")
        chat = try_get(update, "effective_chat") or try_get(message, "chat")
        chat_type = try_get(chat, "type")
        is_private_chat = chat_type == "private"
        is_group_chat = chat_type == "group"
        chat_id = try_get(chat, "id")
        sender = try_get(message, "from_user", "username")
        debug(f"unleash_the_abbot => /unleash {args} executed by {sender}")
        if sender not in WHITELIST:
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
        debug(f"unleash_the_abbot => bot_status={bot_status}")
        if bot_status not in UNLEASH_LEASH:
            return await message.reply_text(
                f"Bad arg: expecting one of {UNLEASH_LEASH}"
            )
        if is_private_chat:
            bot_context = "private"
        elif is_group_chat:
            bot_context = "group"
        debug(f"unleash_the_abbot => bot_context={bot_context}")
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
            debug(f"unleash_the_abbot => abbot={which_abbot}")
        if bot_status in UNLEASH:
            unleashed = which_abbot.unleash()
        else:
            unleashed = which_abbot.leash()

        which_abbot.update_abbots(chat_id, which_abbot)
        response = "unleashed ✅" if unleashed else "leashed ⛔️"
        which_abbot_name = which_abbot.name
        debug(f"unleash_the_abbot => {which_abbot_name} {response}")
        return await message.reply_text(f"{which_abbot_name} {response}")
    except Exception as exception:
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        debug(f"abbot_status => Error={exception}, ErrorMessage={error_msg}")
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"Error={exception} ErrorMessage={error_msg}"
        )
        await message.reply_text(f"Sorry ... taking a nap. Hmu later.")


def abbot_rules():
    # To get an immediate response in a group chat, please tag me in your message or reply directly to a message I have sent previously. Otherwise, I will chime in every so often.
    pass


if __name__ == "__main__":
    TOKEN = TEST_BOT_TOKEN if DEV_MODE else BOT_TOKEN

    APPLICATION = ApplicationBuilder().token(TOKEN).build()
    debug(f"{BOT_NAME} @{BOT_HANDLE} Initialized")

    help_handler = CommandHandler("help", help)
    stop_handler = CommandHandler("stop", stop)
    summary_handler = CommandHandler("summary", summary)
    prompt_handler = CommandHandler("prompt", abbot)
    clean_handler = CommandHandler("clean", clean)
    clean_summary_handler = CommandHandler("both", both)
    unleash_handler = CommandHandler("unleash", unleash_the_abbot)
    status_handler = CommandHandler("status", abbot_status)
    rules_handler = CommandHandler("rules", abbot_rules)
    message_handler = MessageHandler(BaseFilter(), handle_message)

    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(summary_handler)
    APPLICATION.add_handler(prompt_handler)
    APPLICATION.add_handler(clean_handler)
    APPLICATION.add_handler(clean_summary_handler)
    APPLICATION.add_handler(unleash_handler)
    APPLICATION.add_handler(status_handler)
    APPLICATION.add_handler(rules_handler)
    APPLICATION.add_handler(message_handler)

    debug(f"{BOT_NAME} @{BOT_HANDLE} Polling")
    APPLICATION.run_polling()
