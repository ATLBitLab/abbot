import asyncio
from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from src.lib.abbot.nostr_bot import AbbotBuilder, AbbotNostr
from lib.db.mongo import MongoNostr

if __name__ == "__main__":
    mongo_nostr = MongoNostr()
