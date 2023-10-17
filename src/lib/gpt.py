import json
import time
from io import TextIOWrapper, open
from os.path import abspath, isfile
import traceback
from typing import AnyStr

from bot_constants import OPENAI_MODEL
from bot_env import OPENAI_API_KEY

from .logger import debug, error
from .utils import try_except, try_get

import openai
import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


def handle_exception(fn: str, e: Exception):
    error(f"{fn} exception:\n{e}")
    debug(f"{fn} exception:\n{e}")
    traceback.print_exc()
    tb = traceback.format_exc()
    error(f"{fn} traceback:\n{tb}")
    debug(f"{fn} traceback:\n{tb}")


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
        unleashed: bool = False,
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
        self.unleashed: bool = unleashed
        self.sent_intro: bool = sent_intro
        self.chat_history_file_path: AnyStr @ abspath = abspath(f"src/data/gpt/{context}")
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_tokens = self.calculate_chat_history_tokens()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()

    def __str__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"unleashed={self.unleashed}, started={self.started} "
            f"chat_id={self.chat_id}, chat_history_tokens={self.chat_history_tokens})"
        )

    def __repr__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, chat_history={self.chat_history}, "
            f"unleashed={self.unleashed}, started={self.started})"
        )

    def to_json(self):
        return self.__dict__
        

    def _create_history(self) -> TextIOWrapper:
        chat_history_file = open(self.chat_history_file_path, "a+")
        chat_history_file.write(json.dumps(self.gpt_system))
        return chat_history_file

    def _open_history(self):
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
        return chat_history[1:]

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
        return not self.started

    def get_started(self) -> bool:
        return self.started

    def get_sent_intro(self) -> bool:
        return self.sent_intro

    def get_chat_id(self) -> int:
        return self.chat_id

    def sleep(self, t: int) -> str:
        time.sleep(t)
        return True

    def introduce(self) -> bool:
        self.sent_intro = True
        return self.sent_intro

    def fuck_off(self) -> bool:
        self.sent_intro = False
        return not self.sent_intro

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_chat_history(self, chat_message: dict) -> None:
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1

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

    @try_except
    def chat_completion(self) -> str | None:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.chat_history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        response_dict = dict(role="assistant", content=answer)
        if answer:
            self.update_chat_history(response_dict)
        return answer

    @try_except
    def chat_history_completion(self) -> str | Exception:
        # try:
        fn = "chat_history_completion =>"
        debug(fn)
        chat_history_token_count = self.calculate_chat_history_tokens()
        debug(f"{fn} token_count={chat_history_token_count}")
        messages = [self.gpt_system]
        debug(f"{fn} messages={messages}")
        messages.extend(self.chat_history)
        debug(f"{fn} messages={messages}")
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
        )
        debug(f"{fn} response={response}")
        answer = try_get(response, "choices", 0, "message", "content")
        debug(f"{fn} answer={answer}")
        response_dict = dict(role="assistant", content=answer)
        debug(f"{fn} answer={answer}")
        debug(f"{fn} chat_history[-1]={self.chat_history[-1]}")
        self.update_chat_history(response_dict)
        debug(f"{fn} chat_history[-1]={self.chat_history[-1]}")
        return answer
        # except Exception as exception:
        #     handle_exception(exception)

    def update_abbots(self, chat_id: str | int, bot: object) -> None:
        Abbots.BOTS[chat_id] = bot
        debug(f"update_abbots => chat_id={chat_id}")

    def get_abbots(self) -> Abbots.BOTS:
        return Abbots.BOTS

    def get_chat_history(self) -> list:
        return self.chat_history
