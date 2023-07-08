import os

PROGRAM = "ATL BitLab Bot"
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
CHATS_TO_IGNORE = [-911601159]
ADMINS = ["nonni_io", "sbddesign"]
CHEEKY_RESPONSE = [
    "Ah ah ah, you didnt say the magic word ...",
    "Simon says ... no",
    "Access Denied!",
    "Mutombo says no no no",
    "What do we say to the god of ATL BitLab? Not today",
]
import time
import re
import json
from uuid import uuid4
from random import randrange
from datetime import datetime, timedelta
import qrcode
from io import BytesIO

from telegram import Update
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)

from lib.logger import debug
from lib.utils import get_now, http_request
from lib.env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
import openai

openai.api_key = OPENAI_API_KEY

now = get_now()
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id in CHATS_TO_IGNORE:
        return
    mpy = open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()
    message = update.effective_message
    debug(f"[{get_now()}] {PROGRAM}: handle_message - Raw message {message}")
    message_dumps = json.dumps(
        {
            "text": message.text or message.caption,
            "from": message.from_user.first_name,
            "date": message.date.isoformat().split("+")[0].split("T")[0],
        }
    )
    rm_jl = open(RAW_MESSAGE_JL_FILE, "a")
    rm_jl.write(message_dumps)
    rm_jl.write("\n")
    rm_jl.close()


def clean_jsonl_data():
    debug(f"[{get_now()}] {PROGRAM}: clean_jsonl_data - Deduping messages")
    seen = set()  # A set to hold the hashes of each JSON object
    with open(RAW_MESSAGE_JL_FILE, "r") as infile, open(
        MESSAGES_JL_FILE, "w"
    ) as outfile:
        for line in infile:
            obj = json.loads(line)  # Load the JSON object from the line
            if not obj.get("text"):
                continue
            obj_hash = hash(json.dumps(obj, sort_keys=True))  # Hash the JSON object
            if obj_hash not in seen:  # If the hash isn't in the set, it's a new object
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
    debug(f"[{get_now()}] {PROGRAM}: clean_jsonl_data - Deduping done")
    return "Cleaning done!"


def get_dates(lookback=7):
    return [
        (
            (datetime.now() - timedelta(days=1)).date() - timedelta(days=i - 1)
        ).isoformat()
        for i in range(lookback, 0, -1)
    ]


def summarize_messages(days=None):
    summaries = []
    prompts_by_day = {k: "" for k in days}
    for day in days:
        prompt = ""
        messages_file = open(MESSAGES_JL_FILE, "r")
        for line in messages_file.readlines():
            message = json.loads(line)
            message_date = message["date"]
            if day == message_date:
                text = message["text"]
                sender = message["from"]
                message = f"{sender} said {text} on {message_date}\n"
                prompt += message
                print(f"day: {day}")
                print(f"message date: {message_date}")
                print(f"day == message date: {day == message_date}")
        final_prompt = (
            "Summarize the following messages including sender name, date and any urls if present:\n"
            + prompt
        )
        prompts_by_day[day] = final_prompt
    messages_file.close()
    prompts_by_day_file = open(PROMPTS_BY_DAY_FILE, "w")
    prompts_by_day_dump = json.dumps(prompts_by_day)
    prompts_by_day_file.write(prompts_by_day_dump)
    prompts_by_day_file.close()
    debug(f"[{now}] {PROGRAM}: Prompts by day = {prompts_by_day_dump}")
    summary_file = open(SUMMARY_LOG_FILE, "a")
    for day, prompt in prompts_by_day.items():
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4000 - len(prompt),
            n=1,
            stop=None,
            temperature=0.1,
        )
        debug(f"[{now}] {PROGRAM}: OpenAI Response = {response}")
        summary = f"Summary for {day}:\n{response.choices[0].text.strip()}"
        summary_file.write(
            f"{summary}\n----------------------------------------------------------------\n\n"
        )
        summaries.append(summary)
    summary_file.close()
    return summaries


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.username not in ADMINS:
        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    debug(f"[{get_now()}] {PROGRAM}: /clean executed")
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Cleaning ... please wait"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=clean_jsonl_data()
    )


async def both():
    debug(f"[{get_now()}] {PROGRAM}: /both executed")
    await clean()
    await summary()
    return "Messages cleaned. Summaries:"


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.username not in ADMINS:
        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    debug(f"[{get_now()}] {PROGRAM}: /summary executed")
    args = context.args or get_dates()
    arg_len = len(args)
    if arg_len > 0 and arg_len > 2:
        return await update.message.reply_text("Too many args")
    elif arg_len == 1:
        message = f"Generating summary for day {''.join(args)}"
    elif arg_len == 2:
        for arg in args:
            if not re.search("^\d{4}-\d{2}-\d{2}$", arg):
                return await update.message.reply_text(
                    f"Malformed date: expecting form YYYY-MM-DD"
                )
            try:
                datetime.strptime(arg, "%Y-%m-%d").date()
            except Exception as e:
                return await update.message.reply_text(f"Error while parsing date: {e}")
        message = f"Generating summary for each day between {' and '.join(args)}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    summaries = summarize_messages(args)
    for summary in summaries:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=summary
            )
        except Exception as e:
            debug(f"[{get_now()}] {PROGRAM}: summarize error {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"Error: {e}"
            )


async def gptPrompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.username not in ADMINS:
        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    debug(f"[{get_now()}] {PROGRAM}: /prompt executed")
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="GPT is working ... please wait"
    )
    args = context.args
    debug(f"[{get_now()}] {PROGRAM}: args{args}")

    if len(args) > 0:
        prompt_input = " ".join(args)
        try:
            response = http_request(
                "POST",
                "invoices",
                {
                    "correlationId": str(uuid4()),
                    "description": f"ATL BitLab Bot Prompt {prompt_input}",
                    "amount": {"amount": "1.00", "currency": "USD"},
                },
            )
            invoice = response.json()
            invoice_id = invoice.get("invoiceId")

            response = http_request("POST", f"invoices/{invoice_id}/quote")
            quote = response.json()
            ln_invoice = quote.get("lnInvoice")
            qr = qrcode.make(ln_invoice)
            bio = BytesIO()
            qr.save(bio, "PNG")
            bio.seek(0)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=bio,
                caption=f'To get the response to your prompt: "{prompt_input}"\nPlease pay the invoice:\n{ln_invoice}',
            )
        except Exception as e:
            print(e)
        paid = False
        timer = quote.get("expirationInSec")
        while timer > 0:
            response = http_request("GET", f"invoices/{invoice_id}")
            check = response.json()
            paid = check.get("state") == "PAID"
            if paid:
                break
            timer -= 1
            time.sleep(1)
        if not paid:
            try:
                response = http_request("PATCH", f"invoices/${invoice_id}/cancel")
                data = response.json()
                state = data.state
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice Expired / {state}!",
                )
            except Exception as e:
                print(e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Thanks for your payment! Generating response ... please wait!",
        )
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt_input,
            max_tokens=4000 - len(prompt_input),
            n=1,
            stop=None,
            temperature=0.1,
        )
        answer = response.choices[0].text.strip()
    else:
        return await update.message.reply_text("You didn't provide any arguments.")
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"GPT says: {answer}"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.username not in ADMINS:
        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    debug(f"[{get_now()}] {PROGRAM}: /stop executed")
    await context.bot.stop_poll(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.id,
        text="Bot stopped! Use /start to begin polling.",
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Run `/start` to start listening for messages. Available commands:\n\n\
        `/summary`\
            Produce daily summaries\n\
            Args:\
                default ⇒ produce daily summaries for the past 7 days\n\
                date ⇒ produce summary for date\n\
                    e.g. 2023-07-05\n\
                start end ⇒ produce daily summaries from start to end\n\
                    e.g 2023-07-02 2023-07-05\n\
                start number ⇒ produce daily summaries from start + numbers of days (0-index)\n\
                    e.g. 2023-07-02 2 ⇒ 2023-07-02 to 2023-07-04\n\
        `/clean`\
            Dedupe and remove bad chars from the raw messages\n\
            Recommend using `/clean` then `/summary` or `/both` to ensure best output\n\
        `/both` run clean and summary; args for /summary apply\n\
        `/prompt`\n\
            gpt-prompt ⇒ send gpt-prompt to gpt\n\
        /help show help menu",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.username not in ADMINS:
        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    debug(f"[{get_now()}] {PROGRAM}: Bot /start")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot started. Run /help for usage guide",
    )
    message_handler = MessageHandler(BaseFilter(), handle_message)
    application.add_handler(message_handler)


def main():
    debug(f"[{get_now()}] {PROGRAM}: Init Bot")
    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    stop_handler = CommandHandler("stop", stop)
    application.add_handler(stop_handler)
    summary_handler = CommandHandler("summary", summary)
    application.add_handler(summary_handler)
    prompt_handler = CommandHandler("prompt", gptPrompt)
    application.add_handler(prompt_handler)
    clean_handler = CommandHandler("clean", clean)
    application.add_handler(clean_handler)
    clean_summary_handler = CommandHandler("both", both)
    application.add_handler(clean_summary_handler)
    debug(f"[{get_now()}] {PROGRAM}: Polling!")
    application.run_polling()
