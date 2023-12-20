from telegram import Message
from telegram.ext.filters import BaseFilter

from lib.utils import try_get
from lib.abbot.config import BOT_TELEGRAM_USER_ID, BOT_TELEGRAM_USERNAME


class FilterAbbotReply(BaseFilter):
    def filter(self, message: Message):
        reply_to_message = try_get(message, "reply_to_message")
        is_bot = try_get(reply_to_message, "from_user", "is_bot")
        username = try_get(reply_to_message, "from_user", "username")
        user_id = try_get(reply_to_message, "from_user", "id")
        replied_to_bot = bool(reply_to_message and is_bot)
        bot_is_abbot = bool(username == BOT_TELEGRAM_USERNAME or user_id == BOT_TELEGRAM_USER_ID)
        return replied_to_bot and bot_is_abbot
