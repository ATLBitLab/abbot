import os
import io
import json

import openai
from telegram import Message
from env import OPENAI_API_KEY
from lib.logger import debug

from lib.utils import try_get


class GPT:
    OPENAI_MODEL = "gpt-3.5-turbo-16k"

    def __init__(self, name, handle, context, personality, unleashed=False):
        self.GPT_MESSAGE_HISTORY = os.path.abspath(f"data/gpt/{context}_abbot.jsonl")

        openai.api_key = OPENAI_API_KEY
        self.model = self.OPENAI_MODEL
        self.name = name
        self.handle = handle
        self.context = context
        self.personality = personality
        self.messages_append = io.open(self.GPT_MESSAGE_HISTORY, "a")
        self.messages_read = io.open(self.GPT_MESSAGE_HISTORY, "r").readlines()
        self.messages = [json.loads(message) for message in self.messages_read]
        self.content = [dict(role="system", content=personality)]
        self.unleashed = unleashed
        self.started = True

        print("__init__ self.messages_append", self.messages_append)
        print("__init__ self.messages_read", self.messages_read)
        print("__init__ self.messages", self.messages)
        print("__init__ self.content", self.content)

    def __str__(self) -> str:
        return f"GPT(name={self.name}, handle={self.handle}, personality={self.personality})"

    def __repr__(self) -> str:
        return f"GPT(model={self.model},\
                    name={self.name},\
                    handle={self.handle},\
                    context={self.context},\
                    personality={self.personality},\
                    messages={self.messages},\
                    content={self.content},\
                    unleashed={self.unleashed},\
                    started={self.started})"

    def start(self) -> bool:
        self.started = True
        return self.started

    def stop(self) -> bool:
        self.started = False
        return self.started

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_message_content(self, telegram_message: Message | str) -> None:
        prompt = (
            try_get(telegram_message, "text")
            if type(telegram_message) == Message
            else telegram_message
        )
        message_dict = dict(role="user", content=prompt)
        self.content.append(message_dict)
        self.messages_append.write(f"{json.dumps(message_dict)}\n")
        print("self.content", self.content)
        print("self.messages_append", self.messages_append)

    def chat_completion(self) -> str | None:
        try:
            response = openai.ChatCompletion.create(
                model=self.model, messages=self.content, temperature=0.5
            )
            return try_get(response, "choices", 0, "message", "content")
        except Exception as e:
            debug(f"Error: GPT => chat_completion => exception={e}")
            return None
