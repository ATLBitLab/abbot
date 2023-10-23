from lib.logger import debug_logger
from src.lib.abbot import telegram, nostr

if __name__ == "__main__":
    telegram.run()
    nostr.run()
