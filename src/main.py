from sys import argv
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from lib.logger import debug_logger
from lib.bot.config import BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_TOKEN, TEST_BOT_TOKEN
from lib.bot.handlers import (
    start,
    stop,
    rules,
    unleash,
    admin_kill,
    admin_nap,
    admin_plugin,
    admin_status,
    admin_unplug,
    handle_message,
)

ARGS = argv[1:]
DEV_MODE = "-d" in ARGS or "--dev" in ARGS

if __name__ == "__main__":
    TOKEN = TEST_BOT_TOKEN if DEV_MODE else BOT_TOKEN
    APPLICATION = ApplicationBuilder().token(TOKEN).build()

    BOT_NAME = f"t{BOT_NAME}" if DEV_MODE else BOT_NAME
    BOT_HANDLE = f"test_{BOT_TELEGRAM_HANDLE}" if DEV_MODE else BOT_TELEGRAM_HANDLE

    debug_logger.log(f"{BOT_NAME} @{BOT_HANDLE} Initialized")

    _unplug_handler = CommandHandler("unplug", admin_unplug)
    _plugin_handler = CommandHandler("plugin", admin_plugin)
    _kill_handler = CommandHandler("kill", admin_kill)
    _nap_handler = CommandHandler("nap", admin_nap)
    _status_handler = CommandHandler("status", admin_status)
    APPLICATION.add_handler(_unplug_handler)
    APPLICATION.add_handler(_plugin_handler)
    APPLICATION.add_handler(_kill_handler)
    APPLICATION.add_handler(_nap_handler)
    APPLICATION.add_handler(_status_handler)

    help_handler = CommandHandler("help", help)
    rules_handler = CommandHandler("rules", rules)
    start_handler = CommandHandler("start", start)
    stop_handler = CommandHandler("stop", stop)
    unleash_handler = CommandHandler("unleash", unleash)
    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(rules_handler)
    APPLICATION.add_handler(start_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(unleash_handler)

    message_handler = MessageHandler(BaseFilter(), handle_message)
    APPLICATION.add_handler(message_handler)

    debug_logger.log(f"{BOT_NAME} @{BOT_HANDLE} Polling")
    APPLICATION.run_polling()
