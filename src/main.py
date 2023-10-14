from sys import argv

ARGS = argv[1:]
DEV_MODE = "-d" in ARGS or "--dev" in ARGS

from lib.bot.config import (
    BOT_TOKEN,
    TEST_BOT_TOKEN,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
)
from bot import debug_logger, error_logger, deconstruct_error
from telegram.ext.filters import BaseFilter, Entity
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from bot import handle_mention, handle_message, start, stop

try:
    TOKEN = TEST_BOT_TOKEN if DEV_MODE else BOT_TOKEN
    APPLICATION = ApplicationBuilder().token(TOKEN).build()
    debug_logger.log(f"{BOT_NAME} {BOT_TELEGRAM_HANDLE} Initialized")
    help_handler = CommandHandler("help", help)
    stop_handler = CommandHandler("stop", stop)
    start_handler = CommandHandler("start", start)
    message_handler = MessageHandler(Entity("mention"), handle_mention)
    message_handler = MessageHandler(BaseFilter(), handle_message)

    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(start_handler)
    APPLICATION.add_handler(message_handler)

    debug_logger.log(f"{BOT_NAME} {BOT_TELEGRAM_HANDLE} Polling")
    APPLICATION.run_polling()
except Exception as exception:
    cause, traceback, args = deconstruct_error(exception)
    error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
    error_logger.log(f"handle_message => Error={exception}, ErrorMessage={error_msg}")
