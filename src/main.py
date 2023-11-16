import asyncio
from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.logger import bot_debug
from lib.abbot.nostr_bot import NostrBotBuilder

nostr_abbot: NostrBotBuilder = NostrBotBuilder()


if __name__ == "__main__":
    try:
        nostr_abbot.add_relays_connect_and_start_client()
        # event_loop = asyncio.new_event_loop()
        nostr_abbot.run()
        # event_loop.run_forever()
    except KeyboardInterrupt:
        bot_debug.log("Interrupt received, shutting down.")
        bot_debug.log("Shutting down...")
        # event_loop.stop()
        bot_debug.log("Shutdown complete.")
