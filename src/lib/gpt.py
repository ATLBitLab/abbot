import openai
from telegram import Message

from lib.utils import try_get


class   GPT:
    def __init__(self, api_key, model, gpt_type):
        openai.api_key = api_key
        self.model = model
        self.gpt_type = gpt_type
        self.messages = []

    def update_messages(self, update):
        self.messages.append(update)

    def chat_completion(self, telegram_message: Message | str):
        prompt = try_get(telegram_message, "text") if type(telegram_message) == Message else telegram_message
        message_dict = dict(role="user", content=prompt)
        self.update_messages(message_dict)
        print('self.messages', self.messages)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.messages,
        )
        return try_get(response, "choices", 0, "message", "content")
