STARTED = None
PROGRAM = "ATL BitLab Bot"
<<<<<<< HEAD

import os
import json
=======
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
CHATS_TO_IGNORE = [-911601159]
ADMINS = ["nonni_io", "sbddesign"]
MEMBERS = ["alex_lewin"]
WHITELIST = ADMINS + MEMBERS
CHEEKY_RESPONSE = [
    "Ah ah ah, you didnt say the magic word ...",
    "Simon says ... no",
    "Access Denied!",
    "Mutombo says no no no",
    "What do we say to the god of ATL BitLab? Not today",
]
>>>>>>> 06e1881 (server)
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
from lib.env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from help_menu import help_menu_message
import openai

BOT_DATA = io.open(os.path.abspath("data/bot_data.json"), "r")
BOT_DATA_OBJ = json.load(BOT_DATA)
CHATS_TO_IGNORE = try_get(BOT_DATA_OBJ, "chats")
WHITELIST = try_get(BOT_DATA_OBJ, "whitelist")
CHEEKY_RESPONSES = try_get(BOT_DATA_OBJ, "responses")
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
openai.api_key = OPENAI_API_KEY
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
now = datetime.now()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.effective_message
        if not STARTED:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Bot must be started. Run /start to begin listening to and storing messages or /help for usage guide",
            )
        if update.effective_chat.id in CHATS_TO_IGNORE:
            return
        mpy = io.open(MESSAGES_PY_FILE, "a")
        mpy.write(update.to_json())
        mpy.write("\n")
        mpy.close()
        debug(f"[{now}] {PROGRAM}: handle_message - Raw message {message}")
        message_dumps = json.dumps(
            {
                **message.to_dict(),
                "new": True,
                "from": message.from_user.username,
                "date": message.date.isoformat().split("+")[0].split("T")[0],
            }
        )
        rm_jl = io.open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dumps)
        rm_jl.write("\n")
        rm_jl.close()
    


def clean_jsonl_data():
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping messages")
    seen = set()  # A set to hold the hashes of each JSON object
    with io.open(RAW_MESSAGE_JL_FILE, "r") as infile, io.open(
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
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping done")
    return "Cleaning done!"


def summarize_messages(days=None):
    summaries = []
    prompts_by_day = {k: "" for k in days}
    for day in days:
        prompt = ""
        messages_file = io.open(MESSAGES_JL_FILE, "r")
        for line in messages_file.readlines():
            message = json.loads(line)
            message_date = message["date"]
            if day == message_date:
                text = message["text"]
                sender = message["from"]
                message = f"{sender} said {text} on {message_date}\n"
                prompt += message
        final_prompt = (
            "Summarize the key points in this text. Separate the key points with an empty line, another line with 10 equal signs, and then another empty line. \n\n"
            + prompt
        )
        prompts_by_day[day] = final_prompt
    messages_file.close()
    prompts_by_day_file = io.open(PROMPTS_BY_DAY_FILE, "w")
    prompts_by_day_dump = json.dumps(prompts_by_day)
    prompts_by_day_file.write(prompts_by_day_dump)
    prompts_by_day_file.close()
    debug(f"[{now}] {PROGRAM}: Prompts by day = {prompts_by_day_dump}")
    summary_file = io.open(SUMMARY_LOG_FILE, "a")
    for day, prompt in prompts_by_day.items():
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4000 - len(prompt),
            temperature=0,
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
    sender = update.effective_message.from_user.username
    debug(f"[{now}] {PROGRAM}: /clean executed by {sender}")
    if update.effective_message.from_user.username not in WHITELIST:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSES[randrange(len(CHEEKY_RESPONSES))],
        )
    debug(f"[{now}] {PROGRAM}: /clean executed")
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
    else:
        args = get_dates()
        message = f"Generating summary for each day in the past week: {args}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    summaries = summarize_messages(args)
    for summary in summaries:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=summary
            )
        except Exception as e:
            debug(f"[{now}] {PROGRAM}: summarize error {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"Error: {e}"
            )


<<<<<<< HEAD
async def atl_bitlab_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Working on your request"
        )
        args = context.args
        debug(f"[{now}] {PROGRAM}: atl_bitlab_bot - args: {args}")

        if len(args) <= 0:
            return await update.message.reply_text("Error: You didn't provide a prompt")
        prompt = " ".join(args)
        prompt_len = len(prompt)
        if len(prompt) >= 3095:
            return await update.message.reply_text(
                "Error: Prompt too long. Max token len = 3095"
            )
        prompt = prompt[: prompt_len - 22] if prompt_len >= 184 else prompt
        if sender not in WHITELIST:
            strike = Strike(str(uuid4()), f"ATL BitLab Bot: Payer - {sender}, Prompt - {prompt}", None)
            paid = strike.invoice()
            ln_invoice, timer = strike.quote()
            qr = qr_code(ln_invoice)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr,
                caption=f"To get your answer: \"{prompt}\"\nPlease pay the invoice:\n\n`{ln_invoice}`",
            )
            while not paid:
                paid = strike.paid()
                if paid:
                    break
                elif timer == 0:
                    response = strike.expire_invoice() 
                    data = response.json()
                    state = data.state
                    return await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Invoice expired {state}",
                    )
                timer -= 1
                time.sleep(1)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expires in {timer}",
                )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Thank you for supporting ATL BitLab. Generating your answer.",
            )
=======
async def gpt_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prompter = update.effective_message.from_user.username
        if prompter not in WHITELIST:
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

        if len(args) <= 0:
            return await update.message.reply_text("Error: You didn't provide a prompt")
        prompt = " ".join(args)
        prompt_len = len(prompt)
        if len(prompt) >= 3095:
            return await update.message.reply_text("Error: Prompt too long. Max token len = 3095")
        prompt = prompt[:prompt_len - 22] if prompt_len >= 184 else prompt
        response = http_request(
            "POST",
            "invoices",
            {
                "correlationId": str(uuid4()),
                "description": f"ATL BitLab Bot: Payer - {prompter}, Prompt - {prompt}",
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
            caption=f'To get the response to your prompt: "{prompt}"\nPlease pay the invoice:\n{ln_invoice}',
        )
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
            response = http_request("PATCH", f"invoices/${invoice_id}/cancel")
            data = response.json()
            state = data.state
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Invoice Expired / {state}!",
            )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Thanks for your payment! Generating response ... please wait!",
        )
>>>>>>> 06e1881 (server)
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4095 - len(prompt),
<<<<<<< HEAD
            temperature=0,
        )
        answer = response.choices[0].text.strip()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Answer:\n\n{answer}"
        )
    except Exception as e:
        debug(f"[{now}] {PROGRAM}: atl_bitlab_bot - /prompt Error: {e}")
=======
            n=1,
            stop=None,
            temperature=0.1,
        )
        answer = response.choices[0].text.strip()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"GPT says: {answer}"
        )
    except Exception as e:
>>>>>>> 06e1881 (server)
        return await update.message.reply_text(f"Error: {e}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
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
    debug(f"[{now}] {PROGRAM}: /help executed by {update.effective_message.from_user.username}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_menu_message,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
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


def main():
    debug(f"[{now}] {PROGRAM}: Init Bot")
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)
    stop_handler = CommandHandler("stop", stop)
    application.add_handler(stop_handler)
    summary_handler = CommandHandler("summary", summary)
    application.add_handler(summary_handler)
<<<<<<< HEAD
    prompt_handler = CommandHandler("prompt", atl_bitlab_bot)
=======
    prompt_handler = CommandHandler("prompt", gpt_prompt)
>>>>>>> 06e1881 (server)
    application.add_handler(prompt_handler)
    clean_handler = CommandHandler("clean", clean)
    application.add_handler(clean_handler)
    clean_summary_handler = CommandHandler("both", both)
    application.add_handler(clean_summary_handler)
    message_handler = MessageHandler(BaseFilter(), handle_message)
    application.add_handler(message_handler)
    debug(f"[{now}] {PROGRAM}: Polling!")
    application.run_polling()
