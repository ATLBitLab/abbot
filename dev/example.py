import logging
import datetime
import time
from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, MessageEntity
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import openai
from lib.env import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)

def handle_message(update: Update, context: CallbackContext) -> None:
    """
    This function handles the /handle_message command
    """
    message = update.message
    print(f"Message: {message.text}\nFrom: {message.from_user.first_name}\n")


def main() -> None:
    print('Main!')
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    message_handler = MessageHandler(Filters.text & (~Filters.command), handle_message)

    # Register commands
    updater.dispatcher.add_handler(message_handler)

    print('Polling!')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()