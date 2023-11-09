from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.abbot.nostr_bot import nostr_bot, AbbotNostr, NostrBotBuilder

if __name__ == "__main__":
    nostr_bot.run()
