from lib.abbot.config import BOT_NAME, BOT_TELEGRAM_HANDLE, BOT_TELEGRAM_TOKEN

from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from lib.logger import debug_logger
from lib.abbot.handlers import (
    leash,
    start,
    stop,
    rules,
    help,
    unleash,
    admin_nap,
    admin_kill,
    admin_plugin,
    admin_status,
    admin_unplug,
    handle_message,
)


def run_nostr():
    # TODO: create nostr run fn using backend handlers
    pass
