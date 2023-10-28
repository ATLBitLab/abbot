from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.abbot import telegram_bot
from lib.abbot import nostr_bot

if __name__ == "__main__":
    if NOSTR_MODE:
        nabbot = nostr_bot.build()
        while True:
            nabbot.run_relay_sync()
    elif TELEGRAM_MODE:
        telegram_bot.build().run_polling()
