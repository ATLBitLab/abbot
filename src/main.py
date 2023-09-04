from functools import wraps
from sys import argv

ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
DEV_MODE = "-d" in ARGS or "--dev" in ARGS
CLEAN_SUMMARY = CLEAN and SUMMARY

from constants import BOT_NAME, BOT_HANDLE

BOT_NAME = f"t{BOT_NAME}" if DEV_MODE else BOT_NAME
BOT_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE

import os
import json
import time
import re
import io

from random import randrange
from help_menu import help_menu_message
from uuid import uuid4
from datetime import datetime
from lib.utils import get_dates, try_get, try_gets

from telegram import Update, Message
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)

from lib.logger import debug
from lib.utils import qr_code
from lib.api.strike import Strike
from lib.gpt import GPT

from env import BOT_TOKEN, TEST_BOT_TOKEN, STRIKE_API_KEY

BOT_DATA = io.open(os.path.abspath("data/bot_data.json"), "r")
BOT_DATA_OBJ = json.load(BOT_DATA)
CHATS_TO_IGNORE = try_get(BOT_DATA_OBJ, "chats", "ignore")
CHATS_TO_INCLUDE_SUMMARY = try_get(BOT_DATA_OBJ, "chats", "include", "summary")
# CHATS_TO_INCLUDE_UNLEASH = try_get(BOT_D`ATA_OBJ, "chats", "include", "unleash")
CHAT_NAME_MAPPING = try_get(BOT_DATA_OBJ, "chats", "mapping", "nameToShortName")
WHITELIST = try_get(BOT_DATA_OBJ, "whitelist")
CHEEKY_RESPONSES = try_get(BOT_DATA_OBJ, "responses", "cheeky")
PITHY_RESPONSES = try_get(BOT_DATA_OBJ, "responses", "pithy")

TECH_BRO_BITCOINER = try_get(BOT_DATA_OBJ, "personalities", "TECH_BRO_BITCOINER")
HELPFUL_ASSISTANT = try_get(BOT_DATA_OBJ, "personalities", "HELPFUL_ASSISTANT")

prompt_abbot = GPT(BOT_NAME, BOT_HANDLE, "prompt", HELPFUL_ASSISTANT)
summary_abbot = GPT(f"s{BOT_NAME}", BOT_HANDLE, "summary", HELPFUL_ASSISTANT)
group_abbot = GPT(f"g{BOT_NAME}", BOT_HANDLE, "group", TECH_BRO_BITCOINER, True)
private_abbot = GPT(f"p{BOT_NAME}", BOT_HANDLE, "private", TECH_BRO_BITCOINER, True)

RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
now = datetime.now()
now_iso = now.isoformat()
now_iso_clean = now_iso.split("+")[0].split("T")[0]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"handle_message => Raw update {update}")
    mpy = io.open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()

    message = (
        try_get(update, "message")
        or try_get(update, "effective_message")
        or update.message
    )
    all_message_data = try_gets(message)
    debug(f"handle_message => all_message_data={all_message_data}")
    if not message:
        debug(f"handle_message => Update.effective_message missing! {message}")
        return
    chat = try_get(update, "effective_chat") or try_get(message, "chat")
    debug(f"handle_message => Raw chat {chat}")
    message_text = try_get(message, "text")

    debug(f"handle_message => Raw message {message}")
    username = try_get(message, "from_user", "username")
    date = (try_get(message, "date") or now).isoformat().split("+")[0].split("T")[0]

    name = try_get(chat, "first_name", default=username)
    chat_id = try_get(chat, "id")
    chat_title = try_get(chat, "title", default="atlantabitdevs")
    if chat_title != "atlantabitdevs":
        chat_title = try_get(CHAT_NAME_MAPPING, chat_title, default="atlantabitdevs")
    chat_type = try_get(chat, "type")
    chat_id = try_get(chat, "id")
    private_chat = chat_type == "private"

    if chat_id in CHATS_TO_IGNORE:
        debug(f"handle_message => Chat ignored {chat_id}")
        return
    if not summary_abbot.started:
        debug(f"handle_message => {summary_abbot.name} stopped")
        return await message.reply_text(
            f"{summary_abbot.name} stopped, please run /start @{BOT_HANDLE}"
        )
    message_dump = json.dumps(
        {
            "id": chat_id,
            "title": chat_title,
            "from": username,
            "name": name,
            "date": date,
            "new": True,
        }
    )
    debug(f"handle_message => message_dump={message_dump}")
    if not private_chat or chat_id not in CHATS_TO_IGNORE:
        debug(f"handle_message => Private chat={private_chat}")
        rm_jl = io.open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dump)
        rm_jl.write("\n")
        rm_jl.close()

    which_abbot = None
    use_group_abbot = (
        not private_chat
        and chat_id not in CHATS_TO_INCLUDE_SUMMARY
        and group_abbot.unleashed
    )
    use_private_abbot = private_chat and private_abbot.unleashed
    if use_group_abbot:
        debug(f"handle_message => Use group_abbot={use_group_abbot}")
        which_abbot = group_abbot
    elif use_private_abbot:
        debug(f"handle_message => Use private_abbot={use_private_abbot}")
        which_abbot = private_abbot

    if not which_abbot:
        debug(f"handle_message => No abbot! which_abbot={which_abbot}")
        return

    handle = f"@{which_abbot.handle}"
    history_len = len(which_abbot.chat_history)
    if use_group_abbot:
        if handle not in message_text or history_len % 5 != 0:
            debug(f"handle_message => {handle} not tagged, message_text={message_text}")
            debug(f"handle_message => len % 5 != 0, len={history_len}")
            return

    debug(f"handle_message => All checks passed! which_abbot={which_abbot}")
    error = f"Please try again later. {which_abbot.name} leashed ⛔️"
    which_abbot.update_chat_history(dict(role="user", content=message_text))
    answer = which_abbot.chat_completion()
    response = error if not answer else answer
    return await message.reply_text(response)


def clean_jsonl_data():
    debug(f"clean_jsonl_data => Deduping messages")
    seen = set()
    with io.open(RAW_MESSAGE_JL_FILE, "r") as infile, io.open(
        MESSAGES_JL_FILE, "w"
    ) as outfile:
        for line in infile:
            obj = json.loads(line)
            if not obj.get("text"):
                continue
            obj_hash = hash(json.dumps(obj, sort_keys=True))
            if obj_hash not in seen:
                seen.add(obj_hash)
                obj_date = obj.get("date")
                plus_in_date = "+" in obj_date
                t_in_date = "T" in obj_date
                plus_and_t = plus_in_date and t_in_date
                if plus_and_t:
                    obj["date"] = obj_date.split("+")[0].split("T")[0]
                elif plus_in_date:
                    obj["date"] = obj_date.split("+")[0]
                elif t_in_date:
                    obj["date"] = obj_date.split("T")[0]
                obj_text = obj.get("text")
                apos_in_text = "'" in obj_text
                if apos_in_text:
                    obj["text"] = obj_text.replace("'", "")
                outfile.write(json.dumps(obj))
                outfile.write("\n")
    infile.close()
    outfile.close()
    debug(f"clean_jsonl_data => Deduping done")
    return "Cleaning done!"


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"clean => /clean executed by {sender}")
    if update.effective_message.from_user.username not in WHITELIST:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
        )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Cleaning ... please wait"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=clean_jsonl_data()
    )


async def both(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await clean(update, context)
    await summary(update, context)
    return "Messages cleaned. Summaries:"


def whitelist_gate(sender):
    return sender not in WHITELIST


def summarize_messages(chat, days=None):
    # Separate the key points with an empty line, another line with 10 equal signs, and then another empty line. \n
    try:
        summaries = []
        prompts_by_day = {k: "" for k in days}
        for day in days:
            prompt_content = ""
            messages_file = io.open(MESSAGES_JL_FILE, "r")
            for line in messages_file.readlines():
                message = json.loads(line)
                message_date = try_get(message, "date")
                if day == message_date:
                    text = try_get(message, "text")
                    sender = try_get(message, "from")
                    message = f"{sender} said {text} on {message_date}\n"
                    prompt_content += message
            if prompt_content == "":
                continue
            prompts_by_day[day] = prompt_content
        messages_file.close()
        prompts_by_day_file = io.open(PROMPTS_BY_DAY_FILE, "w")
        prompts_by_day_dump = json.dumps(prompts_by_day)
        prompts_by_day_file.write(prompts_by_day_dump)
        prompts_by_day_file.close()
        debug(f"summarize_messages => Prompts by day = {prompts_by_day_dump}")
        summary_file = io.open(SUMMARY_LOG_FILE, "a")
        prompt = "Summarize the text after the asterisk. Split into paragraphs where appropriate. Do not mention the asterisk. * \n"
        for day, content in prompts_by_day.items():
            summary_abbot.update_message_content(f"{prompt}{content}")
            answer = summary_abbot.chat_completion()
            debug(f"summarize_messages => OpenAI Response = {answer}")
            summary = f"Summary {day}:\n{answer.strip()}"
            summary_file.write(f"{summary}\n--------------------------------\n\n")
            summaries.append(summary)
        summary_file.close()
        return True, summaries
    except Exception as e:
        debug(f"summarize_messages => error: {e}")
        return False, e


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        success, response = summarize_messages(chat, dates)
        if not success:
            return await message.reply_text(response)
        for summary in response:
            await message.reply_text(summary)
    except Exception as error:
        debug(f"summary => error: {error}")
        return await message.reply_text(f"Error: {error}")


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
        prompt_abbot.update_message_content(prompt)
        answer = prompt_abbot.chat_completion()
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
    debug(f"help => /help executed by {update.effective_message.from_user.username}")
    message_text = update.message.text
    if f"@{BOT_HANDLE}" not in message_text:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"For help, tag @{BOT_HANDLE} in the help command: e.g. /help @{BOT_HANDLE}",
        )
    await context.bot.send_message(
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


async def abbot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = (
            try_get(update, "message")
            or try_get(update, "effective_message")
            or update.message
        )
        sender = try_get(message, "from_user", "username")

        debug(f"abbot_status => /status executed by {sender}")
        if sender not in WHITELIST:
            cheek = CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))]
            return await message.reply_text(cheek)
        for abbot in (prompt_abbot, summary_abbot, group_abbot, private_abbot):
            await message.reply_text(abbot.status())
    except Exception as e:
        error = e.with_traceback(None)
        debug(f"abbot_status => Error: {error}")
        await message.reply_text(text=f"Error: {error}")


async def unleash_the_abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args

        UNLEASH = ("1", "True", "On")
        LEASH = ("0", "False", "Off")
        UNLEASH_LEASH = (*UNLEASH, *LEASH)

        message = update.effective_message
        message_text = update.message.text
        sender = message.from_user.username

        bot_toggle = try_get(context, "args", 0, default="False").capitalize()
        bot_type = try_get(context, "args", 1, default="group")
        possible_bot_types = ("group", "private")

        if bot_type not in possible_bot_types:
            err = f"Bad arg: expecting one of {possible_bot_types}"
            return await message.reply_text(err)

        debug(f"unleash_the_abbot => /unleash {args} executed by {sender}")
        if sender not in WHITELIST:
            cheek = CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))]
            return await message.reply_text(cheek)
        elif f"@{BOT_HANDLE}" not in message_text:
            return await message.reply_text(
                f"To unleash @{BOT_HANDLE}, run unleash with proper args: e.g. /unleash 1 group @{BOT_HANDLE}",
            )

        if bot_toggle not in UNLEASH_LEASH:
            err = f"Bad arg: expecting one of {UNLEASH_LEASH}"
            return await message.reply_text(err)

        which_bot = group_abbot
        which_bot_name = group_abbot.name
        if bot_type == "private":
            which_bot = private_abbot
            which_bot_name = private_abbot.name

        if bot_toggle in UNLEASH:
            which_bot.unleash()
            await message.reply_text(f"{which_bot_name} unleashed ✅")
        else:
            which_bot.leash()
            await message.reply_text(f"{which_bot_name} leashed ⛔️")

        debug(f"unleash_the_abbot => Unleashed={which_bot.unleashed}")
    except Exception as e:
        error = e.with_traceback(None)
        debug(f"unleash_the_abbot => Error: {error}")
        await message.reply_text(text=f"Error: {error}")


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
    message_handler = MessageHandler(BaseFilter(), handle_message)

    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(summary_handler)
    APPLICATION.add_handler(prompt_handler)
    APPLICATION.add_handler(clean_handler)
    APPLICATION.add_handler(clean_summary_handler)
    APPLICATION.add_handler(unleash_handler)
    APPLICATION.add_handler(status_handler)
    APPLICATION.add_handler(message_handler)

    debug(f"{BOT_NAME} @{BOT_HANDLE} Polling")
    APPLICATION.run_polling()
