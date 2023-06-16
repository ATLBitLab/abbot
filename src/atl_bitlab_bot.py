PROGRAM = "ATL BitLab Bot"
RAW_MESSAGE_JL_FILE = "data/raw_messages.jsonl"
MESSAGES_JL_FILE = "data/messages.jsonl"
SUMMARY_LOG_FILE = "data/summaries.txt"
MESSAGES_PY_FILE = "data/backup/messages.py"
PROMPTS_BY_DAY_FILE = "data/backup/prompts_by_day.py"

import json
import openai

from lib.logger import debug
from lib.utils import get_now
from lib.env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import BaseFilter

openai.api_key = OPENAI_API_KEY
now = get_now()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    clean_jsonl_data()


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
                outfile.write(json.dumps(obj))
                outfile.write("\n")
    infile.close()
    outfile.close()
    debug(f"[{get_now()}] {PROGRAM}: clean_jsonl_data - Deduping done")


def summarize_messages():
    print("~~~~~~~~~~~~~ START ~~~~~~~~~~~~~~~~~~\n\n\n")
    max_len = 3000
    summaries = []
    yesterday = (datetime.now() - timedelta(days=1)).date()
    one_week = 7
    days = [yesterday - timedelta(days=i - 1) for i in range(one_week, 0, -1)]
    prompts_by_day = {k.isoformat(): [] for k in days}
    prompts = []
    for day in days:
        prompt = ""
        mf = open(MESSAGES_JL_FILE, "r")
        for line in mf.readlines():
            message = json.loads(line)
            date = datetime.fromisoformat(message["date"]).date()
            if day == date:
                text = message["text"]
                sender = message["from"]
                message = f"{sender}: {text}\n"
                if len(prompt) >= max_len:
                    # print(f"max len reached!")
                    # print(f"prompt: {prompt}")
                    prompts_by_day[day.isoformat()].append(prompt)
                    prompt = message
                    # print(f"prompts: {prompts}")
                else:
                    prompt += message
            else:
                print(f"day: {day}")
                print(f"message date: {date}")
                print(f"day == message date: {day == date}")
    mf.close()
    pbdf = open(PROMPTS_BY_DAY_FILE, "w")
    pbdf.write(json.dumps(prompts_by_day))
    pbdf.close()
    # prompt = "Summarize the following text include sender, text and urls:\n" + prompt
    # debug(f"[{now}] {PROGRAM}: Prompt = {prompt}")
    #     response = openai.Completion.create(
    #         model="text-davinci-003",
    #         prompt=prompt,
    #         max_tokens=4000 - len(prompt),
    #         n=1,
    #         stop=None,
    #         temperature=0.1,
    #         # top_p=0.1
    #     )
    #     debug(f"[{now}] {PROGRAM}: OpenAI Response = {response}")
    #     summary = f"Summary for {day}:\n{response.choices[0].text.strip()}"
    #     f = open(SUMMARY_LOG_FILE, "a")
    #     f.write(summary)
    #     f.write(
    #         "\n----------------------------------------------------------------\n\n"
    #     )
    #     summaries.append(summary)
    # return summaries


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summaries = await summarize_messages()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summaries)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"[{get_now()}] {PROGRAM}: /stop executed")
    await context.bot.stop_poll(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.id,
        text="Bot stopped! Use /start to begin polling.",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"[{get_now()}] {PROGRAM}: /start executed")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot started. Use /summarize to generate a summary of the past week's messages.",
    )


def init():
    debug(f"[{get_now()}] {PROGRAM}: Init Bot")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    start_handler = CommandHandler("start", start)
    stop_handler = CommandHandler("stop", stop)
    summarize_handler = CommandHandler("summarize", summarize)
    message_handler = MessageHandler(BaseFilter(), handle_message)
    application.add_handler(start_handler)
    application.add_handler(stop_handler)
    application.add_handler(summarize_handler)
    application.add_handler(message_handler)
    debug(f"[{get_now()}] {PROGRAM}: Polling!")
    application.run_polling()
