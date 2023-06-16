import json
import openai

from lib.logger import logger, debug
from lib.utils import get_now_date, get_now
from lib.env import (
    TELEGRAM_BOT_TOKEN,
    OPENAI_API_KEY,
    MESSAGE_LOG_FILE,
    SUMMARY_LOG_FILE,
    PROGRAM,
)
from datetime import datetime, timedelta
import pytz

utc = pytz.UTC
edt = pytz.timezone("America/New_York")

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
    f = open("messages.py", "a")
    f.write(update.to_json())
    f.write("\n")
    message = update.effective_message
    debug(f"[{get_now()}] {PROGRAM}: handle_message - Raw message {message}")
    message_dumps = json.dumps(
        {
            "text": message.text or message.caption,
            "from": message.from_user.first_name,
            "date": message.date.isoformat(),
        }
    )
    f = open(MESSAGE_LOG_FILE, "a")
    f.write(message_dumps)
    f.write("\n")


def summarize_messages():
    now_date = get_now_date()
    one_week = 8
    days = [now_date - timedelta(days=i - 1) for i in range(one_week, 0, -1)]
    summaries = []
    for day in days:
        logger.debug(f"[{now}] {PROGRAM}: summarize - Summarizing for {day}!")
        # Read message log and select messages from past week
        # Summary, key points,
        prompt = ""
        f = open(MESSAGE_LOG_FILE, "r")
        for line in f.readlines():
            message = json.loads(line)
            date = datetime.fromisoformat(message["date"]).date()
            if day == date:
                text = message["text"]
                sender = message["from"]
                prompt += f"Summarize the following messages into bullets including who sent it, what was said and any urls:\n[{date}] {sender}: {text}\n"
        
        debug(f"[{now}] {PROGRAM}: Prompt = {prompt}")
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4000 - len(prompt),
            n=1,
            stop=None,
            temperature=0.1,
            # top_p=0.1
        )
        debug(f"[{now}] {PROGRAM}: OpenAI Response = {response}")
        summary = f"Summary for {day}:\n{response.choices[0].text.strip()}"
        f = open(SUMMARY_LOG_FILE, "a")
        f.write(summary)
        f.write(
            "\n----------------------------------------------------------------\n\n"
        )
        summaries.append(summary)
    return summaries


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
