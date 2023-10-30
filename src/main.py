import asyncio
from sys import argv

from abbot_builder import AbbotBuilder

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.abbot import nostr_bot
from lib.db.mongo import MongoNostr

if __name__ == "__main__":
    mongo_nostr = MongoNostr()
    abbot = AbbotBuilder().set_host("127.0.0.1").set_port(8888)

    n_abbot = nostr_bot.build()
    n_abbot.run_relay_sync()
    for event in n_abbot.poll_for_events():
        print(event)

    for notice in n_abbot.poll_for_notices():
        print(notice)

    asyncio.run(abbot.run())
