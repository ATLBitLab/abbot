import json
import openai

from lib.logger import logger, debug
from lib.utils import get_now
from lib.env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, MESSAGE_LOG_FILE, PROGRAM
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    debug(f"[{get_now()}] {PROGRAM}: handle_message - Raw message {prompt}")
    message_dumps = json.dumps(
        {
            "text": message.text,
            "from": message.from_user.first_name,
            "date": message.date.isoformat(),
        }
    )
    f = open(MESSAGE_LOG_FILE, "a")
    f.write(message_dumps)
    f.write("\n")


def summarize_past_week():
    logger.debug(f"[{get_now()}] {PROGRAM}: summarize_past_week - Summarizing!")
    now = get_now()
    one_week_ago = now - timedelta(weeks=1)

    # Read message log and select messages from past week
    # Summary, key points,
    prompt = ""
    prompts = []
    max_len = 2000
    f = open(MESSAGE_LOG_FILE, "r")
    for line in f.readlines():
        message = json.loads(line)
        text = message["text"]
        sender = message["from"]
        date = datetime.fromisoformat(message["date"].split("+")[0])
        if date >= one_week_ago:
            context = f"[{date}] {sender}: {text}\n"
            prompt += context
            prompt_len = len(prompt)
            if prompt_len >= max_len:
                prompts.append(prompt)
                prompt = ""
    print("prompts", prompts)
    prompt_statement = "Summarize the following text include sender, text and urls:\n"
    summaries = []
    for prompt in prompts:
        prompt = prompt_statement + prompt
        debug(f"[{get_now()}] {PROGRAM}: Prompt {prompt}")
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=4000 - len(prompt),
            n=1,
            stop=None,
            temperature=0.5,
        )
        debug(f"[{get_now()}] {PROGRAM}: OpenAI Respone {response}")
        summaries.append(
            f"Summary from {one_week_ago} to {now}:\n{response.choices[0].text.strip()}"
        )
    return summaries


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summary = await summarize_past_week()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summary)


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
    summarize_handler = CommandHandler("summarize", summarize)
    message_handler = MessageHandler(BaseFilter(), handle_message)
    application.add_handler(start_handler)
    application.add_handler(summarize_handler)
    application.add_handler(message_handler)
    debug(f"[{get_now()}] {PROGRAM}: Polling!")
    application.run_polling()
