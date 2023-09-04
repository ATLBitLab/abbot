from os.path import abspath, isfile
from io import TextIOWrapper
import json

import openai
from lib.logger import debug
from constants import OPENAI_MODEL
from lib.utils import try_get


class GPT:
    DATA_GPT_ABSOLUTE_PATH = abspath("data/gpt/")

    def __init__(self, name, handle, context, personality, unleashed=False):
        import env

        openai.api_key = env.OPENAI_API_KEY
        GPT_SYSTEM = dict(role="system", content=personality)

        self.model = OPENAI_MODEL
        self.name = name
        self.handle = handle
        self.context = context
        self.personality = personality
        self.unleashed = unleashed
        self.started = True

        self.chat_history_file_path = (
            f"{GPT.DATA_GPT_ABSOLUTE_PATH}/{context}_abbot.jsonl"
        )
        self.chat_history_file = self._open_history()
        self.chat_history_file_cursor = self.chat_history_file.tell()
        self.chat_history = self._inflate_history()

        if self.chat_history_file.tell() > 0:
            return

        if len(self.chat_history) > 0:
            return

        if try_get(self.chat_history, 0) == GPT_SYSTEM:
            return

        if json.dumps(GPT_SYSTEM) in self.chat_history_file.read():
            return

        self.chat_history_file.write(f"{json.dumps(GPT_SYSTEM)}\n")
        self.chat_history.insert(0, GPT_SYSTEM)

    def __str__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"personality={self.personality}, unleashed={self.unleashed})"
        )

    def __repr__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, chat_history={self.chat_history}, "
            f"unleashed={self.unleashed}, started={self.started})"
        )

    def _create_history(self) -> str:
        open(self.chat_history_file_path, "x")
        return open(self.chat_history_file_path, "r+")

    def _open_history(self) -> TextIOWrapper:
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "r+")

    def _close_history(self):
        self.chat_history_file.close()

    def _inflate_history(self):
        chat_history = []
        self.chat_history_file.seek(0)
        for message in self.chat_history_file.readlines():
            if not message:
                continue
            chat_history.append(json.loads(message))
        self.chat_history_file.seek(self.chat_history_file_cursor)
        return chat_history

    def status(self) -> dict(started=str, unleashed=str):
        return dict(name=self.name, started=self.started, unleashed=self.unleashed)

    def start(self) -> bool:
        self.started = True
        self._open_history()
        return self.started

    def stop(self) -> bool:
        self.started = False
        self.chat_history_file.close()
        return self.started

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        debug(f"{__name__} => update_chat_history => chat_message={chat_message}")
        self.chat_history.append(chat_message)
        debug(f"{__name__} => update_chat_history => chat_history={self.chat_history}")
        self.chat_history_file.write(f"{json.dumps(chat_message)}\n")

    def chat_completion(self) -> str | None:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.chat_history,
                temperature=1,
                frequency_penalty=0.5,
                presence_penalty=0.5,
            )
            answer = try_get(response, "choices", 0, "message", "content")
            response_dict = dict(role="assistant", content=answer)
            if answer:
                self.update_chat_history(response_dict)
            return answer
        except Exception as e:
            debug(f"Error: GPT => chat_completion => exception={e}")
            return None
