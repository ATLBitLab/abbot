import json
from io import TextIOWrapper, open
from os.path import abspath, isfile
from typing import AnyStr

from constants import OPENAI_MODEL, YD
from env import OPENAI_API_KEY

from lib.logger import debug, error
from lib.utils import try_get

import openai
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


class Abbots:
    BOTS: dict = dict()

    def __init__(self, abbots: list):
        bots: dict = dict()
        for abbot in abbots:
            name = try_get(abbot, "chat_id")
            bots[name] = abbot
        self.BOTS.update(bots)
        print("gpt => Abbots => self.BOTS", self.BOTS.keys())

    def __str__(self) -> str:
        _str_ = f"\nAbbots(BOTS="
        BOTS = self.BOTS.values()
        for bot in BOTS:
            _str_ += f"{bot.__str__()})\n"
        return f"{_str_.rstrip()})\n"

    def __repr__(self) -> str:
        return f"Abbots(BOTS={self.BOTS})"

    def get_bots(self) -> dict:
        return self.BOTS


class GPT(Abbots):
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        context: str,
        chat_id: int = None,
        started: bool = False,
        sent_intro: bool = False,
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
        self.sent_intro: bool = sent_intro

        chat_history_abs_filepath: AnyStr @ abspath = abspath(f"src/data/gpt/{context}")
        self.chat_history_file_path: str = (
            f"{chat_history_abs_filepath}/{chat_id}.jsonl"
            if chat_id
            else f"{chat_history_abs_filepath}/{context}_abbot.jsonl"
        )
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_token_length = self.calculate_chat_history_tokens()

    def __str__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"unleashed={self.unleashed}, started={self.started} "
            f"chat_id={self.chat_id}, chat_history_token_length={self.chat_history_token_length})"
        )

    def __repr__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, chat_history={self.chat_history}, "
            f"unleashed={self.unleashed}, started={self.started})"
        )

    def _create_history(self) -> TextIOWrapper:
        try:
            chat_history_file = open(self.chat_history_file_path, "a+")
            chat_history_file.write(json.dumps(self.gpt_system))
            return chat_history_file
        except Exception as exception:
            error(f"_create_history => exception={exception}")
            exit(1)

    def _open_history(self) -> TextIOWrapper:
        try:
            if not isfile(self.chat_history_file_path):
                return self._create_history()
            return open(self.chat_history_file_path, "a+")
        except Exception as exception:
            error(f"_open_history => exception={exception}")
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
            error(f"chat_id={self.chat_id} message={message}")
            error(f"_inflate_history => exception={exception}")
            exit(1)

    def all_status(self) -> dict:
        status = dict(
            name=self.name,
            started=self.started,
            unleashed=self.unleashed,
        )
        if not self.chat_id:
            return status
        status.update(dict(chat_id=self.chat_id))
        return status

    def status(self) -> dict:
        return self.__str__()

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

    def knock(self) -> bool:
        self.sent_intro = True
        return self.sent_intro

    def fuck_off(self) -> bool:
        self.sent_intro = False
        return self.sent_intro

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        try:
            if not chat_message:
                return
            self.chat_history.append(chat_message)
            self.chat_history_file.write("\n" + json.dumps(chat_message))
            self.chat_history_len += 1
        except Exception as exception:
            error(f"update_chat_history => exception={exception}")
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
            error(f"Error: chat_completion => exception={exception}")
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
            debug(
                f"chat_history_completion {YD} token_count={chat_history_token_count}"
            )
            if chat_history_token_count > 2500:
                chat_context = [
                    self.gpt_system,
                    self.chat_history[len(self.chat_history_len) / 2 :],
                ]
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=chat_context,
            )
            answer = try_get(response, "choices", 0, "message", "content")
            response_dict = dict(role="assistant", content=answer)
            self.update_chat_history(response_dict)
            return answer
        except Exception as exception:
            error(f"chat_history_completion => exception={exception}")
            raise exception

    def update_abbots(self, chat_id: str | int, bot: object) -> None:
        try:
            Abbots.BOTS[chat_id] = bot
            debug(f"update_abbots => chat_id={chat_id}")
        except Exception as exception:
            error(f"Error: update_abbots => exception={exception}")
            raise exception

    def get_abbots(self) -> Abbots.BOTS:
        return Abbots.BOTS

    def get_chat_history(self) -> list:
        return self.chat_history


"""
reverse_chat_history = [self.personality, *self.chat_history[::-1]]
                total = 0
                index = 0
                shortened_history = [self.personality]
                for message_dict in reverse_chat_history:
                    content = try_get(message_dict, "content")
                    shortened_history.insert(1, message_dict)
                    total += self.calculate_tokens(content)
                    index += 1
                    if total >= 2500:
                        chat_context = shortened_history
                        break
"""
