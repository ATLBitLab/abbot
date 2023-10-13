import json
from io import TextIOWrapper, open
from os.path import abspath, isfile
from typing import AnyStr

from constants import OPENAI_MODEL
from bot_config import OPENAI_API_KEY

from lib.logger import debug_logger, error_logger
from lib.utils import try_get

import openai
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


class Abbit:
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        chat_id: int = None,
        started: bool = False,
        sent_intro: bool = False,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id
        self.started: bool = started
        self.unleashed: bool = started
        self.sent_intro: bool = sent_intro
        self.chat_history_file_path: AnyStr @ abspath = abspath(
            f"src/data/{name}.jsonl"
        )
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_token_length = self.calculate_chat_history_tokens()

    def __str__(self) -> str:
        return (
            f"Abbit(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"unleashed={self.unleashed}, started={self.started} "
            f"chat_id={self.chat_id}, chat_history_token_length={self.chat_history_token_length})"
        )

    def __repr__(self) -> str:
        return (
            f"Abbit(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, chat_history={self.chat_history}, "
            f"unleashed={self.unleashed}, started={self.started})"
        )

    def _create_history(self) -> TextIOWrapper:
        try:
            chat_history_file = open(self.chat_history_file_path, "a+")
            chat_history_file.write(json.dumps(self.gpt_system))
            return chat_history_file
        except Exception as exception:
            error_logger.log(f"_create_history => exception={exception}")
            exit(1)

    def _open_history(self) -> TextIOWrapper:
        try:
            if not isfile(self.chat_history_file_path):
                return self._create_history()
            return open(self.chat_history_file_path, "a+")
        except Exception as exception:
            error_logger.log(f"_open_history => exception={exception}")
            exit(1)

    def _close_history(self) -> None:
        self.chat_history_file.close()

    def _inflate_history(self) -> list:
        try:
            chat_history = []
            self.chat_history_file_cursor = self.chat_history_file.tell()
            self.chat_history_file.seek(0)
            for message in self.chat_history_file.readlines():
                if not message:
                    continue
                chat_history.append(json.loads(message))
            self.chat_history_file.seek(self.chat_history_file_cursor)
            return chat_history
        except Exception as exception:
            error_logger.log(f"chat_id={self.chat_id} message={message}")
            error_logger.log(f"_inflate_history => exception={exception}")
            exit(1)

    def status(self) -> (str, str):
        return self.started, self.sent_intro

    def start(self) -> bool:
        self.started = True
        self._open_history()
        return True

    def stop(self) -> bool:
        self.started = False
        self.chat_history_file.close()
        return True

    def hello(self) -> bool:
        self.sent_intro = True
        return self.sent_intro

    def goodbye(self) -> bool:
        self.sent_intro = False
        return self.sent_intro

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        try:
            if not chat_message:
                return
            self.chat_history.append(chat_message)
            self.chat_history_file.write("\n" + json.dumps(chat_message))
            self.chat_history_len += 1
        except Exception as exception:
            error_logger.log(f"update_chat_history => exception={exception}")
            exit(1)

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
            error_logger.log(f"chat_completion => exception={exception}")
            raise exception

    def tokenize(self, content: str) -> list:
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        return len(self.tokenize(content))

    def calculate_chat_history_tokens(self) -> int:
        total = 0
        for data in self.chat_history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    def chat_history_completion(self) -> str | Exception:
        try:
            chat_context = self.chat_history
            chat_history_token_count = self.calculate_chat_history_tokens()
            debug_logger.log(
                f"chat_history_completion => token_count={chat_history_token_count}"
            )
            if chat_history_token_count > 5000:
                reverse_chat_history = [self.personality, *self.chat_history[::-1]]
                total = 0
                index = 0
                shortened_history = [self.personality]
                for message_dict in reverse_chat_history:
                    content = try_get(message_dict, "content")
                    shortened_history.insert(message_dict)
                    total += self.calculate_tokens(content)
                    index += 1
                    if total >= 3923:
                        chat_context = shortened_history
                        break
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=chat_context,
            )
            answer = try_get(response, "choices", 0, "message", "content")
            response_dict = dict(role="assistant", content=answer)
            self.update_chat_history(response_dict)
            return answer
        except Exception as exception:
            error_logger.log(f"chat_history_completion => exception={exception}")
            raise exception

    def get_chat_history(self) -> list:
        return self.chat_history
