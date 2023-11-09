from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.logger import debug_logger
from lib.abbot.nostr_bot import nostr_bot

if __name__ == "__main__":
    debug_logger.log(f"Initializing nostr bot ...")
    nostr_bot.run()
    debug_logger.log(f"Initialized nostr bot ...")
