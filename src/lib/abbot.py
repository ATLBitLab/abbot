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
from bot.config import BOT_COUNT, OPENAI_API_KEY
from bot.exceptions.abbot_exeption import try_except

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


def handle_exception(fn: str, e: Exception):
    error_logger.log(f"{fn} exception:\n{e}")
    debug_logger.log(f"{fn} exception:\n{e}")
    traceback.print_exc()
    tb = traceback.format_exc()
    error_logger.log(f"{fn} traceback:\n{tb}")
    debug_logger.log(f"{fn} traceback:\n{tb}")


class Config:
    def __init__(
        self,
        started,
        introduced,
        unleashed,
        count,
    ):
        self.started = started
        self.introduced = introduced
        self.unleashed = unleashed
        self.count = count

    def to_dict(self):
        return self.__dict__

    def update_config(self, data: dict):
        self.__dict__.update(data)
        return self.__dict__


class Bots:
    abbots: dict = dict()

    def __init__(self, bots: list):
        for bot in bots:
            name = try_get(bot, "chat_id")
            self.abbots[name] = bot
        print("gpt: Bots: self.abbots", self.abbots.keys())

    def __str__(self) -> str:
        _str_ = f"\nAbbots(abbots="
        for bot in self.abbots:
            _str_ += f"{bot.__str__()})\n"
        return f"{_str_.rstrip()})\n"

    def __repr__(self) -> str:
        return f"Bots(abbots={self.abbots})"

    def get_abbots(self) -> dict:
        return self.abbots

    def to_dict(self) -> dict:
        return self.__dict__


class Abbot(Config, Bots):
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
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id

        self.config_file_path: AnyStr @ abspath = abspath(f"src/data/chat/{context}/config/{chat_id}.json")
        # handle case of new chat
        self.config_file: TextIOWrapper = open(self.config_file_path, "r+")
        self.config_json: dict = json.load(self.config_file)
        self.config = Config(**self.config_json)
        self.started: bool = self.config.started
        self.unleashed: bool = self.config.unleashed
        self.count = self.config.count if self.unleashed else None
        self.introduced: bool = self.config.introduced

        self.chat_history_file_path: AnyStr @ abspath = abspath(f"src/data/chat/{context}/content/{chat_id}.jsonl")
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_tokens = self.calculate_chat_history_tokens()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()

    def __str__(self) -> str:
        fn = "__str__:"
        abbot_str = (
            f"Abbot(model={self.model}, name={self.name}, "
            f"handle={self.handle}, unleashed={self.unleashed}, "
            f"started={self.started}, chat_id={self.chat_id}, "
            f"chat_history_token_length={self.chat_history_token_length})"
        )
        debug_logger.log(f"{fn} abbot_str={abbot_str}")
        return abbot_str

    def __repr__(self) -> str:
        fn = "__repr__:"
        abbot_repr = (
            f"Abbot(model={self.model}, name={self.name}, "
            f"handle={self.handle}, personality={self.personality}, "
            f"chat_history={self.chat_history}, unleashed={self.unleashed}, started={self.started})"
        )
        debug_logger.log(f"{fn} abbot_repr={abbot_repr}")
        return abbot_repr

    def to_dict(self) -> dict:
        return self.__dict__

    def _create_history(self) -> TextIOWrapper:
        fn = "_create_history:"
        chat_history_file = open(self.chat_history_file_path, "a+")
        debug_logger.log(f"{fn} at {self.chat_history_file_path}")
        return chat_history_file

    def _open_history(self) -> TextIOWrapper:
        fn = "_open_history:"
        debug_logger.log(f"{fn} at {self.chat_history_file_path}")
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "a+")

    def _inflate_history(self) -> list:
        fn = "_inflate_history:"
        debug_logger.log(f"{fn} at {self.chat_history_file_path}")
        chat_history = []
        self.chat_history_file_cursor = self.chat_history_file.tell()
        self.chat_history_file.seek(0)
        for message in self.chat_history_file.readlines():
            if not message:
                continue
            chat_history.append(json.loads(message))
        self.chat_history_file.seek(self.chat_history_file_cursor)
        debug_logger.log(f"{fn} chat_history={chat_history}")
        return chat_history

    def get_config(self) -> dict:
        return self.config.to_dict()

    def get_chat_id(self) -> int:
        fn = "get_chat_id:"
        debug_logger.log(fn)
        return self.chat_id

    def update_config(self, new_config: dict):
        self.config.update_config(new_config)
        json.dump(self.config, self.config_file)

    def start(self) -> bool:
        fn = "start:"
        if started:
            debug_logger.log(f"{fn} already started!")
        self.update_config(dict(started=True))
        debug_logger.log(f"{fn} Config.started={Config.started}")
        started = self.config.started
        debug_logger.log(f"{fn} started={started}")
        return started

    def stop(self) -> bool:
        fn = "stop:"
        started = self.config.started
        if not started:
            debug_logger.log(f"{fn} not started!")
        self.update_config(dict(started=False))
        debug_logger.log(f"{fn} Config.started={Config.started}")
        stopped = self.config.started
        debug_logger.log(f"{fn} stopped={stopped}")
        return stopped

    def introduce(self) -> bool:
        fn = "introduce:"
        self.update_config(dict(introduced=True))
        debug_logger.log(f"{fn} Config.introduced={Config.introduced}")
        introduced = self.config.introduced
        debug_logger.log(f"{fn} introduced={introduced}")
        return self.introduced

    def forget(self) -> bool:
        fn = "forget:"
        started = self.config.started
        if not started:
            debug_logger.log(f"{fn} not started!")
            return
        self.update_config(dict(introduced=False))
        debug_logger.log(f"{fn} Config.introduced={Config.introduced}")
        introduced = self.introduced
        debug_logger.log(f"{fn} introduced={introduced}")
        return introduced

    def unleash(self, count: int) -> bool:
        fn = "unleash:"
        self.update_config(dict(unleashed=True, count=count))
        unleashed = self.config.unleashed
        self.config.count = count
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")
        return unleashed

    def leash(self) -> bool:
        fn = "leash:"
        self.update_config(dict(unleashed=False, count=None))
        unleashed = self.config.unleashed
        count = self.config.count
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")
        return unleashed

    def is_started(self) -> bool:
        fn = "is_started:"
        started = self.config.started
        debug_logger.log(f"{fn} {started}")
        return started

    def is_stopped(self) -> bool:
        fn = "is_stopped:"
        stopped = not self.is_started()
        debug_logger.log(f"{fn} {stopped}")
        return stopped

    def is_introduced(self) -> bool:
        fn = "is_introduced:"
        introduced = self.config.introduced
        debug_logger.log(f"{fn} {introduced}")
        return introduced

    def is_forgotten(self) -> bool:
        fn = "is_introduced:"
        forgotten = not self.is_introduced()
        debug_logger.log(f"{fn} {forgotten}")
        return forgotten

    def is_unleashed(self) -> bool:
        fn = "is_unleashed:"
        unleashed = self.config.unleashed
        count = self.config.count
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")
        return unleashed, count

    def is_leashed(self) -> bool:
        fn = "is_leashed:"
        leashed, count = not self.is_unleashed()
        debug_logger.log(f"{fn} unleashed={leashed} count={count}")
        return leashed, count

    def sleep(self, t: int) -> str:
        fn = "sleep:"
        debug_logger.log(fn)
        time.sleep(t)
        return True

    def get_chat_history(self) -> list:
        fn = "get_chat_history:"
        debug_logger.log(fn)
        return self.chat_history

    def tokenize(self, content: str) -> list:
        fn = "tokenize:"
        debug_logger.log(fn)
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        fn = "calculate_tokens:"
        debug_logger.log(fn)
        return len(self.tokenize(content))

    def calculate_chat_history_tokens(self) -> int:
        fn = "calculate_chat_history_tokens:"
        debug_logger.log(fn)
        total = 0
        for data in self.chat_history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        fn = "update_chat_history:"
        debug_logger.log(fn)
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1
        self.chat_history_tokens += len(self.tokenize(try_get(chat_message, "content")))
        return self.chat_history_tokens

    @try_except
    def chat_completion(self) -> str | None:
        fn = "chat_completion:"
        debug_logger.log(fn)
        messages = [self.gpt_system]
        history = self.chat_history
        if self.chat_history_tokens > 5000:
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
        fn = "chat_history_completion:"
        debug_logger.log(fn)
        messages = [self.gpt_system]
        history = self.chat_history
        if self.chat_history_tokens > 5000:
            index = self.chat_history_len // 2
            history = history[index:]
        messages.extend(history)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        response_dict = dict(role="assistant", content=answer)
        self.update_chat_history(response_dict)
        return answer

    def update_abbots(self, chat_id: str | int, bot: object) -> None:
        Bots.abbots[chat_id] = bot
        debug_logger.log(f"update_abbots: chat_id={chat_id}")

    def get_abbots(self) -> Bots.abbots:
        return Bots.abbots

    def abbots_to_dict(self):
        return Bots.__dict__
