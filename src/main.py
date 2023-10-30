from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

from lib.abbot import nostr_bot

if __name__ == "__main__":
    n_abbot = nostr_bot.build()
    while True:
        for event in n_abbot.poll_for_events():
            if event.kind == 21021:
                print(event.tags[0])
                n_abbot.send_greeting_to_channel(event.tags[0][1])
