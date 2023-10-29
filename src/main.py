from lib.logger import debug_logger
from src.lib.abbot import telegram, nostr

if __name__ == "__main__":
<<<<<<< Updated upstream
    telegram.run()
    nostr.run()
=======
    if NOSTR_MODE:
        nostr_bot.build().run_relay_sync()
    elif TELEGRAM_MODE:
        telegram_bot.build().run_polling()
>>>>>>> Stashed changes
