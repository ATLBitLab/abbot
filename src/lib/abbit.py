import json
from io import TextIOWrapper, open
from os.path import abspath, isfile
from typing import AnyStr

from constants import OPENAI_MODEL
from env import OPENAI_API_KEY

from lib.logger import debug, error
from lib.utils import try_get

import openai

class Abbit:
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        context: str,
        chat_id: int = None,
        started: bool = False,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.context: str = context
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id
        self.started: bool = started
        self.unleashed: bool = started

        chat_history_abs_filepath: AnyStr @ abspath = abspath(f"src/data/gpt/{context}")
        self.chat_history_file_path: str = (
            f"{chat_history_abs_filepath}/{chat_id}.jsonl"
            if chat_id
            else f"{chat_history_abs_filepath}/{context}_abbot.jsonl"
        )
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()
        self.chat_history: list = self._inflate_history()

    def __str__(self) -> str:
        return (
            f"Abbit(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"chat_id={self.chat_id}, started={self.started}"
        )

    def __repr__(self) -> str:
        return (
            f"Abbit(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, chat_history={self.chat_history}, "
            f"unleashed={self.unleashed}, started={self.started})"
        )

    def _create_history(self) -> TextIOWrapper:
        chat_history_file = open(self.chat_history_file_path, "a+")
        chat_history_file.write(f"{json.dumps(self.gpt_system)}\n")
        return chat_history_file

    def _open_history(self) -> TextIOWrapper:
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "a+")

    def _close_history(self) -> None:
        self.chat_history_file.close()

    def _inflate_history(self) -> list:
        chat_history = []
        self.chat_history_file_cursor = self.chat_history_file.tell()
        self.chat_history_file.seek(0)
        for message in self.chat_history_file.readlines():
            if not message:
                continue
            chat_history.append(json.loads(message))
        self.chat_history_file.seek(self.chat_history_file_cursor)
        return chat_history

    def status(self) -> dict:
        status = dict(
            name=self.name,
            started=self.started,
            unleashed=self.unleashed,
        )
        if not self.chat_id:
            return status
        status.update(dict(chat_id=self.chat_id))
        return status

    def start(self) -> bool:
        self.started = True
        self.unleashed = self.started
        self._open_history()
        return self.started

    def stop(self) -> bool:
        self.started = False
        self.unleashed = self.started
        self.chat_history_file.close()
        return self.started

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        self.chat_history.append(chat_message)
        self.chat_history_file.write(f"{json.dumps(chat_message)}\n")

    def chat_completion(self) -> str | None:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.chat_history,
            )
            answer = try_get(response, "choices", 0, "message", "content")
            response_dict = dict(role="assistant", content=answer)
            if answer:
                self.update_chat_history(response_dict)
            return answer
        except Exception as exception:
            error(f"Error: chat_completion => exception={exception}")
            return None

    def get_chat_history(self) -> list:
        return self.chat_history
