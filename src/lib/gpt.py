import openai
from telegram import Message

from lib.utils import try_get


class GPT:
    def __init__(self, api_key, model, gpt_type):
        openai.api_key = api_key
        self.model = model
        self.gpt_type = gpt_type
        self.messages = []

    def update_messages(self, telegram_message: Message | str | dict):
        prompt = try_get(telegram_message, "text") if type(telegram_message) == Message else telegram_message
        message_dict = dict(role="user", content=prompt)
        self.messages.append(message_dict)

    def chat_completion(self):
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.messages,
        )
        return try_get(response, "choices", 0, "message", "content")
