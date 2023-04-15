import telegram
from telegram.ext import Updater, MessageHandler, Filters
import openai
from env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

# Set up the Telegram bot using your API token
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Set up the ChatGPT API using your API key
openai.api_key = OPENAI_API_KEY

# Define a function to generate a response using the ChatGPT API
def generate_response(text):
    prompt = "Conversation with user:\n" + text + "\nAI:"
    response = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.7,
    )
    return response.choices[0].text

# Define a function to handle incoming messages
def message_handler(update, context):
    text = update.message.text
    response = generate_response(text)
    bot.send_message(chat_id=update.effective_chat.id, text=response)

# Set up the Telegram bot to listen for incoming messages
updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), message_handler))

# Start the bot
updater.start_polling()
