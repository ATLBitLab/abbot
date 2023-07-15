import os

PROGRAM = "ATL BitLab Bot"
STARTED = False
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")
CHATS_TO_IGNORE = [-911601159, -1001608254734]
ADMINS = ["nonni_io", "sbddesign"]
DEDICATED_DESKS = ["alex_lewin"]
MEMBERS = []
WHITELIST = ADMINS + DEDICATED_DESKS
CHEEKY_RESPONSE = [
    "Ah ah ah, you didnt say the magic word ...",
    "Simon says ... no",
    "Access Denied!",
    "Mutombo says no no no",
    "What do we say to the god of ATL BitLab? Not today",
    "Do not pass go, do not collect $200",
]
import time
import re
import json
from random import randrange
from uuid import uuid4
from datetime import datetime, timedelta

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
from lib.api.strike import Strike
from help_menu import help_menu_message
import openai

openai.api_key = OPENAI_API_KEY
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

now = datetime.now()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.effective_message
        if "/start" not in message and not STARTED:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Bot must be started. Run /start to begin listening to and storing messages or /help for usage guide",
            )
        if update.effective_chat.id in CHATS_TO_IGNORE:
            return
        mpy = open(MESSAGES_PY_FILE, "a")
        mpy.write(update.to_json())
        mpy.write("\n")
        mpy.close()
        debug(f"[{now}] {PROGRAM}: handle_message - Raw message {message}")
        message_dumps = json.dumps(
            {
                "from": message.from_user.first_name,
                "date": message.date.isoformat().split("+")[0].split("T")[0],
                **message.to_dict(),
            }
        )
        rm_jl = open(RAW_MESSAGE_JL_FILE, "a")
        rm_jl.write(message_dumps)
        rm_jl.write("\n")
        rm_jl.close()
    except Exception as e:
        await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Error: {e}",
            )


def clean_jsonl_data():
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping messages")
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
    debug(f"[{now}] {PROGRAM}: clean_jsonl_data - Deduping done")
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
        final_prompt = (
            "Summarize the key points in this text. Separate the key points with an empty line, another line with 10 equal signs, and then another empty line. \n\n"
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
    if update.effective_message.from_user.username not in ADMINS:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
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


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"[{now}] {PROGRAM}: /summary executed by {sender}")
    if sender not in ADMINS:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
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


async def atl_bitlab_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        # debug(f"[{now}] {PROGRAM}: /prompt executed by {sender}")
        # if sender not in WHITELIST:
        #     return await context.bot.send_message(
        #         chat_id=update.effective_chat.id,
        #         text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        #     )
        # debug(f"[{now}] {PROGRAM}: /prompt executed")
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
        if sender not in DEDICATED_DESKS:
            strike = Strike(str(uuid4()), f"ATL BitLab Bot: Payer - {sender}, Prompt - {prompt}", None)
            paid = strike.invoice()
            ln_invoice, timer = strike.quote()
            qr = qr_code(ln_invoice)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr,
                caption=f'To get your answer: "{prompt}"\nPlease pay the invoice:\n`{ln_invoice}`',
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
        return await update.message.reply_text(f"Error: {e}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"[{now}] {PROGRAM}: /stop executed by {sender}")
    if update.effective_message.from_user.username not in ADMINS:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
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
    if sender not in ADMINS:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=CHEEKY_RESPONSE[randrange(len(CHEEKY_RESPONSE))],
        )
    STARTED = True
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot started. Run /help for usage guide",
    )


def main():
    message_handler = MessageHandler(BaseFilter(), handle_message)
    application.add_handler(message_handler)
    debug(f"[{now}] {PROGRAM}: Init Bot")
    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    stop_handler = CommandHandler("stop", stop)
    application.add_handler(stop_handler)
    summary_handler = CommandHandler("summary", summary)
    application.add_handler(summary_handler)
    prompt_handler = CommandHandler("prompt", atl_bitlab_bot)
    application.add_handler(prompt_handler)
    clean_handler = CommandHandler("clean", clean)
    application.add_handler(clean_handler)
    clean_summary_handler = CommandHandler("both", both)
    application.add_handler(clean_summary_handler)
    debug(f"[{now}] {PROGRAM}: Polling!")
    application.run_polling()
