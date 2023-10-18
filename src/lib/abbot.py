import json
import time
import openai
import tiktoken
import traceback
from typing import AnyStr
from .utils import try_get
from io import TextIOWrapper, open
from os.path import abspath, isfile

from constants import OPENAI_MODEL
from .logger import debug_logger, error_logger
from lib.bot.config import BOT_COUNT, OPENAI_API_KEY
from lib.bot.exceptions.abbot_exception import try_except

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


def handle_exception(fn: str, e: Exception):
    error_logger.log(f"{fn} exception:\n{e}")
    debug_logger.log(f"{fn} exception:\n{e}")
    traceback.print_exc()
    tb = traceback.format_exc()
    error_logger.log(f"{fn} traceback:\n{tb}")
    debug_logger.log(f"{fn} traceback:\n{tb}")


class Config:
    def __init__(self, started, unleashed, sent_intro):
        self.started = started
        self.unleashed = unleashed
        self.sent_intro = sent_intro

    def to_dict(self):
        return self.__dict__


class Abbots:
    abbots: dict = dict()

    def __init__(self, bots: list):
        for bot in bots:
            name = try_get(bot, "chat_id")
            self.abbots[name] = bot
        print("gpt => Abbots => self.abbots", self.abbots.keys())

    def __str__(self) -> str:
        _str_ = f"\nAbbots(abbots="
        for bot in self.abbots:
            _str_ += f"{bot.__str__()})\n"
        return f"{_str_.rstrip()})\n"

    def __repr__(self) -> str:
        return f"Abbots(abbots={self.abbots})"

    def get_abbots(self) -> dict:
        return self.abbots

    def to_dict(self) -> dict:
        return self.__dict__


class GPT(Config, Abbots):
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        context: str,
        chat_id: int,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.context: str = context
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id

        self.config_file_path: AnyStr @ abspath = abspath(f"src/data/chat/{context}/config/{chat_id}.json")
        # handle case of new chat
        self.config_file: TextIOWrapper = open(self.config_file_path, "r+")
        self.config_json: dict = json.load(self.config_file)
        Config(**self.config_json)
        self.started: bool = Config.started
        self.unleashed: bool = Config.unleashed
        self.count = BOT_COUNT if self.unleashed else None
        self.sent_intro: bool = Config.sent_intro

        self.chat_history_file_path: AnyStr @ abspath = abspath(f"src/data/chat/{context}/content/{chat_id}.jsonl")
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

    def to_dict(self) -> dict:
        return self.__dict__

    def _create_history(self) -> TextIOWrapper:
        chat_history_file = open(self.chat_history_file_path, "a+")
        chat_history_file.write(json.dumps(self.gpt_system))
        return chat_history_file

    def _open_history(self):
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "a+")

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

    def get_state(self) -> dict:
        return dict(
            name=self.name,
            chat_id=self.chat_id,
            started=self.started,
            unleashed=self.unleashed,
            sent_intro=self.sent_intro,
        )

    def config_to_dict(self) -> dict:
        return Config.to_dict()

    def start(self) -> bool:
        Config.started = True
        return self.started

    def stop(self) -> bool:
        Config.started = False
        return not self.started

    def get_started(self) -> bool:
        return self.started

    def introduce(self) -> bool:
        Config.sent_intro = True
        return self.sent_intro

    def get_sent_intro(self) -> bool:
        return Config.sent_intro

    def get_chat_id(self) -> int:
        return self.chat_id

    def sleep(self, t: int) -> str:
        time.sleep(t)
        return True

    def unleash(self) -> bool:
        Config.unleashed = True
        self.count = BOT_COUNT
        return self.unleashed

    def leash(self) -> bool:
        Config.unleashed = False
        self.count = None
        return not self.unleashed

    def get_chat_history(self) -> list:
        return self.chat_history

    def update_chat_history(self, chat_message: dict) -> None:
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1
        content: str = try_get(chat_message, "content")
        self.chat_history_tokens += len(self.tokenize(content))
        return self.chat_history_tokens

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
        messages = [self.gpt_system]
        history = self.chat_history
        if self.chat_history_tokens > 4500:
            index = self.chat_history_len // 2
            history = history[index:]
        messages.extend(history)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.chat_history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        response_dict = dict(role="assistant", content=answer)
        self.update_chat_history(response_dict)
        return answer

    @try_except
    def chat_history_completion(self) -> str | Exception:
        fn = "chat_history_completion =>"
        debug_logger.log(fn)
        chat_history_token_count = self.calculate_chat_history_tokens()
        debug_logger.log(f"{fn} token_count={chat_history_token_count}")
        messages = [self.gpt_system]
        debug_logger.log(f"{fn} messages={messages}")
        messages.extend(self.chat_history)
        debug_logger.log(f"{fn} messages={messages}")
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
        )
        debug_logger.log(f"{fn} response={response}")
        answer = try_get(response, "choices", 0, "message", "content")
        debug_logger.log(f"{fn} answer={answer}")
        response_dict = dict(role="assistant", content=answer)
        debug_logger.log(f"{fn} answer={answer}")
        debug_logger.log(f"{fn} chat_history[-1]={self.chat_history[-1]}")
        self.update_chat_history(response_dict)
        debug_logger.log(f"{fn} chat_history[-1]={self.chat_history[-1]}")
        return answer

    def update_abbots(self, chat_id: str | int, bot: object) -> None:
        Abbots.abbots[chat_id] = bot
        debug_logger.log(f"update_abbots => chat_id={chat_id}")

    def get_abbots(self) -> Abbots.abbots:
        return Abbots.abbots

    def abbots_to_dict(self):
        return Abbots.__dict__
