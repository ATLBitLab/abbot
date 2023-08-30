STARTED = None
UNLEASHED = False
MESSAGE_COUNT = 0
PROGRAM = "main.py"
BOT_HANDLE = "atl_bitlab_bot"
BOT_NAME = "Abbot"
OPENAI_MODEL = "gpt-3.5-turbo-16k"

import os
import json
import time
import re
import io

from random import randrange
from help_menu import help_menu_message
from uuid import uuid4
from datetime import datetime
from lib.utils import get_dates, try_get

from telegram import Update
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

from env import BOT_TOKEN, TEST_BOT_TOKEN, STRIKE_API_KEY, OPENAI_API_KEY

INTERNET_BRO = "You are a young tech bro in a telegram chat room responding in a way that is concise and uses internet slang."
HELPFUL_ASSISTANT = "You are a helpful assistant"
prompt_abbot = GPT(OPENAI_API_KEY, OPENAI_MODEL, "Abbot", HELPFUL_ASSISTANT)
summary_abbot = GPT(OPENAI_API_KEY, OPENAI_MODEL, "SummaryAbbot", HELPFUL_ASSISTANT)
group_abbot = GPT(OPENAI_API_KEY, OPENAI_MODEL, "GroupAbbot", INTERNET_BRO)
private_abbot = GPT(OPENAI_API_KEY, OPENAI_MODEL, "PrivateAbbot", INTERNET_BRO)
    
BOT_DATA = io.open(os.path.abspath("data/bot_data.json"), "r")
BOT_DATA_OBJ = json.load(BOT_DATA)
CHATS_TO_IGNORE = try_get(BOT_DATA_OBJ, "chats", "ignore")
CHATS_TO_INCLUDE = try_get(BOT_DATA_OBJ, "chats", "include")
CHATS_TO_INCLUDE_NAMES = try_get(BOT_DATA_OBJ, "chats", "names")
WHITELIST = try_get(BOT_DATA_OBJ, "whitelist")
CHEEKY_RESPONSES = try_get(BOT_DATA_OBJ, "responses")
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
now = datetime.now()
now_iso = now.isoformat()
now_iso_clean = now_iso.split("+")[0].split("T")[0]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    message_chat_id = update.effective_chat.id
    if not UNLEASHED and not STARTED:
        debug(f"handle_message => Bot not unleashed or started!")
        return
    if message_chat_id in CHATS_TO_IGNORE:
        debug(f"handle_message => Chat ignored {message_chat_id}")
        return
    mpy = io.open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()
    debug(f"handle_message => Raw message {message}")
    message_dict = message.to_dict()
    chat_dict = message.chat.to_dict()
    message_title = message.chat.title or None
    message_type = message.chat.type or None
    username = message.from_user.username
    first_name = message.chat.first_name or username
    iso_date = message.date.isoformat()
    message_dumps = json.dumps(
        {
            **message_dict,
            "chat": {
                "title": message_title.replace(" ", "").lower()
                if message_title
                else "",
                **chat_dict,
            },
            "new": True,
            "from": username,
            "name": first_name,
            "date": iso_date if iso_date else now_iso_clean,
        }
    )
    private_message = message_type == "private"
    message_text = update.message.text
    if not private_message:
        rm_jl = io.open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dumps)
        rm_jl.write("\n")
        rm_jl.close()
    
    if UNLEASHED:
        if private_message:
            private_abbot.update_messages(message)
            answer = private_abbot.chat_completion()
            return await message.reply_text(answer)
        elif not private_message:
            group_abbot.update_messages(message)
            print('not private_message')
            print('message_text', message_text)

            if f"@{BOT_HANDLE}" in message_text:
                answer = group_abbot.chat_completion()
                return await message.reply_text(answer)
            elif len(group_abbot.messages) % 5 == 0 and message_chat_id != -1001204119993:
                answer = group_abbot.chat_completion()
                return await message.reply_text(answer)


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
            message = dict(
                role="user",
                content=f"{prompt}{content}",
            )
            summary_abbot.update_messages(message)
            response = summary_abbot.chat_completion()
            debug(f"summarize_messages => OpenAI Response = {response}")
            summary = f"Summary {day}:\n{response.choices[0].message.content.strip()}"
            summary_file.write(f"{summary}\n--------------------------------\n\n")
            summaries.append(summary)
        summary_file.close()
        return summaries
    except Exception as e:
        debug(f"summarize_messages => error: {e}")
        raise e


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"/clean executed by {sender}")
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


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        debug(f"summary => /summary executed by {sender}")
        not_whitelisted = whitelist_gate(sender)
        if not_whitelisted:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        args = context.args
        arg_len = len(args)
        if arg_len > 3:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Too many args"
            )
        chat_arg = args[0].replace(" ", "").lower()
        if chat_arg not in CHATS_TO_INCLUDE_NAMES:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Chat name invalid! Expecting one of: {CHATS_TO_INCLUDE_NAMES}",
            )
        chat = chat_arg.replace(" ", "").lower()
        dates = get_dates()
        if arg_len == 1:
            message = f"Generating {chat} summary for past week: {dates}"
        elif arg_len == 2:
            date = args[1]
            if re.search("^\d{4}-\d{2}-\d{2}$", chat):
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Malformed chat: expecting chat name, got {chat}",
                )
            if not re.search("^\d{4}-\d{2}-\d{2}$", date):
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Malformed date: expecting form YYYY-MM-DD, got {date}",
                )
            try:
                datetime.strptime(date, "%Y-%m-%d").date()
            except Exception as e:
                debug(f"summary => datetime.strptime error: {e}")
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Error while parsing date: {e}",
                )
            dates = [args[1]]
            message = f"Generating {chat} summary for {date}"
        elif arg_len == 3:
            dates = args[0:2]
            if re.search("^\d{4}-\d{2}-\d{2}$", chat):
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Malformed chat: expecting chat name, got {chat}",
                )
            for date in dates:
                if not re.search("^\d{4}-\d{2}-\d{2}$", date):
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Malformed date: expecting form YYYY-MM-DD, got {date}",
                    )
                try:
                    datetime.strptime(date, "%Y-%m-%d").date()
                except Exception as e:
                    debug(f"summary => datetime.strptime error: {e}")
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error while parsing date: {e}",
                    )
            message = (
                f"Generating {chat} summary for each day between {' and '.join(args)}"
            )
        else:
            message = f"Generating {chat} summary for each day in the past week: {' '.join(dates)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        summaries = summarize_messages(chat, dates)
        for summary in summaries:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=summary
            )
    except Exception as e:
        debug(f"summary => error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        message = update.effective_message
        debug(f"/prompt executed => sender={sender} message={message}")
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
        prompt_abbot.update_messages(prompt)
        answer = prompt_abbot.chat_completion()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"{answer}"
        )
        debug(f"abbot => Answer: {answer}")
    except Exception as e:
        debug(f"abbot => /prompt Error: {e}")
        return await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Error: {e}"
        )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    message_text = update.message.text
    if "abbot" in message_text:
        debug(f"/stop executed by {sender}")
        if update.effective_message.from_user.username not in WHITELIST:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        debug(f"/stop executed")
        await context.bot.stop_poll(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.id,
            text="Bot stopped! Use /start to begin polling.",
        )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"/help executed by {update.effective_message.from_user.username}")
    message_text = update.message.text
    if f"@{BOT_HANDLE}" not in message_text:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"If you want to start @{BOT_HANDLE}, please tag the bot in the start command: e.g. `/help @{BOT_HANDLE}`",
        )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_menu_message,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    message_text = update.message.text
    if f"@{BOT_HANDLE}" not in message_text:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"If you want to start Abbot @{BOT_HANDLE}, please tag Abbot in the start command: e.g. /start @{BOT_HANDLE}",
        )
    debug(f"/start executed by {sender}")
    if sender not in WHITELIST:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
        )
    global STARTED
    STARTED = True
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Abbot started. Run /help for usage guide",
    )


async def unleash_the_abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        global UNLEASHED
        global MESSAGE_COUNT

        UNLEASH = ("1", "True", "On")
        LEASH = ("0", "False", "Off")
        UNLEASH_LEASH = (*UNLEASH, *LEASH)

        message = update.effective_message
        message_text = update.message.text
        sender = message.from_user.username
        debug(f"unleash_the_abbot => /unleash executed by {sender}")
        if sender not in WHITELIST:
            return await message.reply_text(
                text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        elif f"@{BOT_HANDLE}" not in message_text:
            return
        toggle_arg = try_get(context, "args", 0, default="False").capitalize()
        if toggle_arg not in UNLEASH_LEASH:
            return await message.reply_text(
                text=f"Bad arg: expecting one of {UNLEASH_LEASH}"
            )
        UNLEASHED = True if toggle_arg in UNLEASH else False
        debug(f"unleash_the_abbot => Unleashed={UNLEASHED}")
        if not UNLEASHED:
            return await message.reply_text(text="Abbot not unleashed ⛔️")
        await message.reply_text(text=f"{BOT_NAME} unleashed ✅")
    except Exception as e:
        error = e.with_traceback(None)
        debug(f"unleash_the_abbot => Error: {error}")
        await message.reply_text(text=f"Error: {error}")


def bot_main(DEV_MODE):
    global BOT_HANDLE
    BOT_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE
    global BOT_NAME
    BOT_NAME = "tAbbot" if DEV_MODE else "Abbot"
    TOKEN = TEST_BOT_TOKEN if DEV_MODE else BOT_TOKEN

    APPLICATION = ApplicationBuilder().token(TOKEN).build()
    debug(f"{BOT_NAME} @{BOT_HANDLE} Initialized")

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", help)
    stop_handler = CommandHandler("stop", stop)
    summary_handler = CommandHandler("summary", summary)
    prompt_handler = CommandHandler("prompt", abbot)
    clean_handler = CommandHandler("clean", clean)
    clean_summary_handler = CommandHandler("both", both)
    unleash = CommandHandler("unleash", unleash_the_abbot)
    message_handler = MessageHandler(BaseFilter(), handle_message)

    APPLICATION.add_handler(start_handler)
    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(summary_handler)
    APPLICATION.add_handler(prompt_handler)
    APPLICATION.add_handler(clean_handler)
    APPLICATION.add_handler(clean_summary_handler)
    APPLICATION.add_handler(unleash)
    APPLICATION.add_handler(message_handler)

    debug(f"{BOT_NAME} @{BOT_HANDLE} Polling")
    APPLICATION.run_polling()
