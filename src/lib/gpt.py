import openai
from telegram import Message

from lib.utils import try_get


class GPT:
    def __init__(self, api_key):
        assert (api_key is not None, "OpenAI API key must be supplied")
        openai.api_key = api_key
        self.messages = []

    def update_messages(self, update):
        self.messages.append(update)

    def chat_completion(self, telegram_message: Message):
        prompt = telegram_message.text
        message_dict = dict(role="user", content=prompt)
        self.update_messages(message_dict)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=self.messages,
        )
        return try_get(response, "choices", 0, "message", "content")
