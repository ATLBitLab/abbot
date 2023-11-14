import asyncio
from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.logger import bot_debug
from lib.abbot.nostr_bot import (
    AbbotNostr,
    NostrBuilder,
    NostrHandler,
    handle_dm,
    handle_channel_create,
    handle_channel_create,
    handle_channel_meta,
    handle_channel_message,
    handle_channel_hide,
    handle_channel_mute,
    handle_channel_invite,
)

nostr_bot: NostrBuilder = NostrBuilder().add_handlers(
    [
        NostrHandler(4, handle_dm),
        NostrHandler(40, handle_channel_create),
        NostrHandler(41, handle_channel_meta),
        NostrHandler(42, handle_channel_message),
        NostrHandler(43, handle_channel_hide),
        NostrHandler(44, handle_channel_mute),
        NostrHandler(21021, handle_channel_invite),
    ]
)
abbot_nostr: AbbotNostr = AbbotNostr()


def main():
    bot_debug.log("Nostr abbot initializing ...")
    yield abbot_nostr.start_client()
    bot_debug.log("Nostr abbot initialized")


def shutdown():
    bot_debug.log("Shutting down...")
    abbot_nostr.io_loop.stop()
    bot_debug.log("Shutdown complete.")


if __name__ == "__main__":
    try:
        abbot_nostr.add_relays_connect_and_start_client()
        asyncio.create_subprocess_exec(nostr_bot.run(abbot_nostr))
    except KeyboardInterrupt:
        bot_debug.log("Interrupt received, shutting down.")
        shutdown()
