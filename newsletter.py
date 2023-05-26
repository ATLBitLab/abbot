import json
from env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from datetime import datetime, timedelta
import openai
from pytz import UTC
from telegram.ext import Updater, MessageHandler, Filters

MESSAGE_LOG_FILE = "messages.jsonl"
openai.api_key = OPENAI_API_KEY

def handle_message(update, context):
    message = update.message

    # Store message data as a JSON object in a .jsonl file
    with open(MESSAGE_LOG_FILE, "a") as f:
        json.dump({
            "text": message.text,
            "from": message.from_user.first_name,
            "date": message.date.isoformat(),
        }, f)
        f.write("\n")

def main():
    print('Polling!')
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    message_handler = MessageHandler(Filters.text & (~Filters.command), handle_message)
    updater.dispatcher.add_handler(message_handler)
    updater.start_polling()
    updater.idle()

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
        engine="text-davinci-002",
        prompt=past_week_messages,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5
    )
    summary = response.choices[0].text.strip()
    print(summary)

if __name__ == '__main__':
    main()  # start the bot
    summarize_past_week()  # summarize the past week's messages

