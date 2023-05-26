import json
import openai

from env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, MESSAGE_LOG_FILE
from datetime import datetime, timedelta
from pytz import UTC

from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext.filters import MessageFilter

openai.api_key = OPENAI_API_KEY

class TextMessageFilter(MessageFilter):
    def filter(self, message):
        return message.text and not message.text.startswith('/')

def handle_message(update: Update, context):
    message = update.effective_message

    # Store message data as a JSON object in a .jsonl file
    with open(MESSAGE_LOG_FILE, "a") as f:
        json.dump({
            "text": message.text,
            "from": message.from_user.first_name,
            "date": message.date.isoformat(),
        }, f)
        f.write("\n")

def start_command(update: Update, context):
    update.message.reply_text("Bot started. Use /summarize to generate a summary of past week's messages.")

def summarize_past_week():
    print('Summarizing!')
    one_week_ago = datetime.now(UTC) - timedelta(weeks=1)
    one_week_ago = one_week_ago.replace(tzinfo=None)

    # Read message log and select messages from past week
    past_week_messages = ""
    with open(MESSAGE_LOG_FILE, "r") as f:
        for line in f:
            message = json.loads(line)
            message_date = datetime.fromisoformat(message["date"]).replace(tzinfo=None)
            if message_date > one_week_ago:
                past_week_messages += message["text"] + " "

    # Generate summary using ChatGPT
    response = openai.Completion.create(
        engine="text-davinci-004",
        prompt=past_week_messages,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5
    )
    return response.choices[0].text.strip()

def summarize_command(update: Update, context):
    summary = summarize_past_week()
    update.message.reply_text(summary)

def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    updater = Updater(bot=bot, update_queue=None)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command, filters=TextMessageFilter()))
    dispatcher.add_handler(CommandHandler("summarize", summarize_command, filters=TextMessageFilter()))
    dispatcher.add_handler(MessageHandler(TextMessageFilter(), handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()