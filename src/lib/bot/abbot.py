import openai

from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)

from env import _OPENAI_API_KEY
from constants import (
    GPT_SYSTEM_HELPFUL_ASSISTANT,
    GPT_SYSTEM_TECH_BRO_BITCOINER,
    OPENAI_MODEL,
    GPT_ASSISTANT_TYPES,
)
from lib.utils import try_get, debug
from main import (
    bot_handle_message,
    bot_help,
    bot_stop,
    bot_summary,
    bot_prompt,
    bot_clean,
    bot_both,
    unleash_the_bot,
)


class Abbot:
    def __init__(
        self,
        bot_token: str,
        name: str,
        handle: str,
        unleashed: bool = False,
    ) -> object:
        self.bot_token = bot_token
        self.name = name
        self.handle = handle
        self.unleashed = unleashed
        self.started = True

        self.abbot = ApplicationBuilder().token(bot_token).build()
        debug(f"{name} @{handle} Initialized")
        self.abbot.add_handler(MessageHandler(BaseFilter(), bot_handle_message))
        self.abbot.add_handler(CommandHandler("help", bot_help))
        self.abbot.add_handler(CommandHandler("stop", bot_stop))
        self.abbot.add_handler(CommandHandler("summary", bot_summary))
        self.abbot.add_handler(CommandHandler("prompt", bot_prompt))
        self.abbot.add_handler(CommandHandler("clean", bot_clean))
        self.abbot.add_handler(CommandHandler("both", bot_both))
        self.abbot.add_handler(CommandHandler("unleash", unleash_the_bot))

    def __str__(self):
        return f"Abbot({self.name})"

    def __repr__(self):
        return f"Abbot(name='{self.name}', handle={self.handle}, started={self.started}, unleashed={self.unleashed})"

    def start(self):
        self.started = True
        return self.started, self.abbot.run_polling()

    def stop(self):
        self.started = False
        debug(
            f"{self.name} @{self.handle} stopped! Use /start @{self.handle} to restart bot"
        )
        self.abbot.stop()
        return self.started

    def unleash(self):
        self.unleashed = True
        return self.unleashed

    def leash(self):
        self.unleashed = False
        return self.unleashed


class ChatGPT(Abbot):
    _CHAT_MESSAGES_MAPPING: dict = {}
    """
        {
            "-926629994": {
                "nonni_io": [
                    {
                        "role": "user", "content": "this is a test"
                    }
                ]
            }
        }
    """

    def __init__(self, type: str) -> object:
        openai.api_key: str = _OPENAI_API_KEY
        self.personality: str = (
            GPT_SYSTEM_HELPFUL_ASSISTANT
            if type in GPT_ASSISTANT_TYPES
            else GPT_SYSTEM_TECH_BRO_BITCOINER
        )
        self._messages: list(dict(role=str, content=str)) = [
            dict(role="system", content=self.personality)
        ]
        self.model: str = OPENAI_MODEL
        self.type: str = type
        self.name: str = f"{type}{Abbot.name}"
        self.handle: str = Abbot.handle
        self.unleashed: str = Abbot.unleashed
        self.started: str = Abbot.started

    def __str__(self) -> str:
        return f"ChatGPT(name={self.name}, personality={self.personality})"

    def __repr__(self) -> str:
        return f"""ChatGPT(name={self.name},
                           personality={self.personality},
                           model={self.model},
                           type={self.type},
                           handle={self.handle},
                           unleashed={self.unleashed},
                           started={self.started})"""

    def update_messages(
        self, chat_id: str, username: str, message: dict(role=str, content=str)
    ) -> None:
        chatmap = try_get(self._CHAT_MESSAGES_MAPPING, chat_id)
        chatmap_user = try_get(self._CHAT_MESSAGES_MAPPING, chat_id, username)
        if not chatmap or not chatmap_user:
            self._CHAT_MESSAGES_MAPPING[chat_id] = {username: []}
            chatmap = try_get(self._CHAT_MESSAGES_MAPPING, chat_id)
            chatmap_user = try_get(self._CHAT_MESSAGES_MAPPING, chat_id, username)
        chatmap_user.append(message)
        if len(self._messages) == 1:
            self._messages.append(message)
        elif len(self._messages) == 2:
            self._messages[1] = message

    def chat_completion(self) -> str | None:
        try:
            response = openai.ChatCompletion.create(
                model=self.model, messages=self._messages, tempature=0.5
            )
            return try_get(response, "choices", 0, "message", "content")
        except Exception as e:
            debug(f"Error: GPT => chat_completion => exception={e}")
            return None
