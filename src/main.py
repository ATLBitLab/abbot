from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from src.lib.abbot import telegram_bot
from telegram.ext import ApplicationBuilder


def run_nostr():
    # TODO: create nostr run fn using backend handlers
    pass


if __name__ == "__main__":
    if TELEGRAM_MODE:
        TG_BOT: ApplicationBuilder = telegram_bot.build_telgram_bot().run_polling()
    elif NOSTR_MODE:
        run_nostr()
