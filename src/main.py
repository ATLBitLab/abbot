STARTED = None
PROGRAM = "main.py"

import os
import json
import time
import re
import io

from random import randrange
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
from lib.env import (
    TEST_TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
    OPENAI_API_KEY,
    BOT_HANDLE,
    STRIKE_API_KEY
)
from help_menu import help_menu_message
import openai

BOT_DATA = io.open(os.path.abspath("data/bot_data.json"), "r")
BOT_DATA_OBJ = json.load(BOT_DATA)
CHATS_TO_IGNORE = try_get(BOT_DATA_OBJ, "chats", "ignore")
CHATS_TO_INCLUDE = list(try_get(BOT_DATA_OBJ, "chats", "include"))
CHATS_TO_INCLUDE_NAMES = list(try_get(BOT_DATA_OBJ, "chats", "include").values())
WHITELIST = try_get(BOT_DATA_OBJ, "whitelist")
CHEEKY_RESPONSES = try_get(BOT_DATA_OBJ, "responses")
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
openai.api_key = OPENAI_API_KEY
now = datetime.now()
now_iso = now.isoformat()
now_iso_clean = now_iso.split("+")[0].split("T")[0]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    message_chat_id = update.effective_chat.id
    if not STARTED:
        debug(f"[{now}] {PROGRAM}: handle_message - Bot not started!")
        return
    if message_chat_id in CHATS_TO_IGNORE:
        debug(f"[{now}] {PROGRAM}: handle_message - Chat ignored {message_chat_id}")
        return
    mpy = io.open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()
    debug(f"[{now}] {PROGRAM}: handle_message - Raw message {message}")
    message_dict = message.to_dict()
    chat_dict = message.chat.to_dict()
    message_title = message.chat.title or None
    message_type = message.chat.type or None
    username = message.from_user.username
    first_name = message.from_user.username
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
    if message_type != "private":
        rm_jl = io.open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dumps)
        rm_jl.write("\n")
        rm_jl.close()


def clean_jsonl_data():
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping messages")
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
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping done")
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
        debug(f"[{now}] {PROGRAM}: Prompts by day = {prompts_by_day_dump}")
        summary_file = io.open(SUMMARY_LOG_FILE, "a")
        for day, prompt in prompts_by_day.items():
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "user",
                        "content": f"Summarize the text after the asterisk. Split into paragraphs where appropriate. Do not mention the asterisk. * \n {prompt}",
                    }
                ],
            )
            debug(f"[{now}] {PROGRAM}: OpenAI Response = {response}")
            summary = f"Summary for {day}:\n{response.choices[0].message.content.strip()}"
            summary_file.write(f"{summary}\n--------------------------------\n\n")
            summaries.append(summary)
        summary_file.close()
        return summaries
    except Exception as e:
        debug(f"[{now}] {PROGRAM}: summarize_messages error: {e}")
        raise e


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"[{now}] {PROGRAM}: /clean executed by {sender}")
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
        debug(f"[{now}] {PROGRAM}: /summary executed by {sender}")
        not_whitelisted = whitelist_gate(sender)
        if not_whitelisted:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        debug(f"[{now}] {PROGRAM}: /summary executed")
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
                debug(f"[{now}] {PROGRAM}: summary datetime.strptime error: {e}")
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
                    text=f"Malformed chat: expecting chat name, got {chat}"
                )
            for date in dates:
                if not re.search("^\d{4}-\d{2}-\d{2}$", date):
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Malformed date: expecting form YYYY-MM-DD, got {date}"
                    )
                try:
                    datetime.strptime(date, "%Y-%m-%d").date()
                except Exception as e:
                    debug(f"[{now}] {PROGRAM}: summary datetime.strptime error: {e}")
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error while parsing date: {e}"
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
        debug(f"[{now}] {PROGRAM}: atl_bitlab_bot - summary error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def atl_bitlab_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Working on your request"
        )
        args = context.args
        debug(f"[{now}] {PROGRAM}: atl_bitlab_bot - args: {args}")

        if len(args) <= 0:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error: You didn't provide a prompt")
        prompt = " ".join(args)
        prompt_len = len(prompt)
        if len(prompt) >= 3095:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error: Prompt too long. Max token len = 3095"
            )
        prompt = prompt[: prompt_len - 22] if prompt_len >= 184 else prompt
        if sender not in WHITELIST:
            strike = Strike(STRIKE_API_KEY)
            invoice_id, invoice, expiration = strike.get_invoice(
                str(uuid4()),
                f"ATL BitLab Bot: Payer - {sender}, Prompt - {prompt}",
            )
            qr = qr_code(invoice)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr,
                caption=f'To get your answer: "{prompt}"\nPlease pay the invoice:\n\n`{invoice}`',
            )
            while not strike.invoice_is_paid(invoice_id):
                if expiration == 0:
                    strike.expire_invoice(invoice_id)
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Invoice expired",
                    )
                expiration -= 1
                time.sleep(1)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expires in {expiration}",
                )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Thank you for supporting ATL BitLab. Generating your answer.",
            )
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4095 - len(prompt),
            temperature=0,
        )
        answer = response.choices[0].text.strip()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Answer:\n\n{answer}"
        )
    except Exception as e:
        debug(f"[{now}] {PROGRAM}: atl_bitlab_bot - /prompt Error: {e}")
        return await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    message_text = update.message.text
    if "abbot" in message_text:
        debug(f"[{now}] {PROGRAM}: /stop executed by {sender}")
        if update.effective_message.from_user.username not in WHITELIST:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
            )
        debug(f"[{now}] {PROGRAM}: /stop executed")
        await context.bot.stop_poll(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.id,
            text="Bot stopped! Use /start to begin polling.",
        )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(
        f"[{now}] {PROGRAM}: /help executed by {update.effective_message.from_user.username}"
    )
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
            text=f"If you want to start @{BOT_HANDLE}, please tag the bot in the start command: e.g. /start @{BOT_HANDLE}",
        )
    debug(f"[{now}] {PROGRAM}: /start executed by {sender}")
    if sender not in WHITELIST:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
        )
    global STARTED
    STARTED = True
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot started. Run /help for usage guide",
    )


def bot_main(DEV_MODE):
    global BOT_HANDLE
    BOT_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE
    BOT_TOKEN = TEST_TELEGRAM_BOT_TOKEN if DEV_MODE else TELEGRAM_BOT_TOKEN
    APPLICATION = ApplicationBuilder().token(BOT_TOKEN).build()
    debug(f"[{now}] {PROGRAM}: @{BOT_HANDLE} Initialized")
    start_handler = CommandHandler("start", start)
    APPLICATION.add_handler(start_handler)
    help_handler = CommandHandler("help", help)
    APPLICATION.add_handler(help_handler)
    stop_handler = CommandHandler("stop", stop)
    APPLICATION.add_handler(stop_handler)
    summary_handler = CommandHandler("summary", summary)
    APPLICATION.add_handler(summary_handler)
    prompt_handler = CommandHandler("prompt", atl_bitlab_bot)
    APPLICATION.add_handler(prompt_handler)
    clean_handler = CommandHandler("clean", clean)
    APPLICATION.add_handler(clean_handler)
    clean_summary_handler = CommandHandler("both", both)
    APPLICATION.add_handler(clean_summary_handler)
    message_handler = MessageHandler(BaseFilter(), handle_message)
    APPLICATION.add_handler(message_handler)
    debug(f"[{now}] {PROGRAM}: @{BOT_HANDLE} Polling")
    APPLICATION.run_polling()
