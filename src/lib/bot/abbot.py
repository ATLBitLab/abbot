import json
import time
import openai
import tiktoken
import traceback
from typing import AnyStr
from ..utils import try_get
from io import TextIOWrapper, open
from os.path import abspath, isfile

from constants import OPENAI_MODEL
from lib.logger import debug_logger, error_logger
from lib.bot.config import OPENAI_API_KEY
from lib.bot.exceptions.abbot_exception import AbbotException, try_except

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
        config_dict = self.to_dict()
        config_dict.update(data)


class Bots:
    cl: str = "Bots:"
    abbots: dict = dict()

    def __init__(self, bots: list):
        for bot in bots:
            name = try_get(bot, "chat_id")
            self.abbots[name] = bot
        print("gpt: Bots: self.abbots", self.abbots)

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

    def update_abbots(self, chat_id: str | int, bot: object) -> None:
        fn: str = "update_abbots:"
        self.abbots[chat_id] = bot
        debug_logger.log(f"{self.cl} {fn} update_abbots: chat_id={chat_id}")


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
        self.config_file: TextIOWrapper = self._open_config()
        self.config_json: dict = json.load(self.config_file)
        self.config = Config(**self.config_json)

        self.chat_history_file_path: AnyStr @ abspath = abspath(f"src/data/chat/{context}/content/{chat_id}.jsonl")
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_tokens = self.calculate_chat_history_tokens()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()

    def __str__(self) -> str:
        fn = "__str__:"
        abbot_str = (
            f"Abbot(model={self.model}, name={self.name}, handle={self.handle}, chat_id={self.chat_id}, chat_history_tokens={self.chat_history_tokens}"
            f"started={self.config.started}, unleashed={self.config.unleashed}, )"
        )
        debug_logger.log(f"{fn} abbot_str={abbot_str}")
        return abbot_str

    def __repr__(self) -> str:
        fn = "__repr__:"
        abbot_repr = (
            f"Abbot(chat_id={self.chat_id}, name={self.name}, "
            f"handle={self.handle}, personality={self.personality}, "
            f"chat_history_len={self.chat_history_len}, chat_history_tokens={self.chat_history_tokens}"
            f"self.config={self.config})"
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

    def _create_config(self) -> TextIOWrapper:
        fn = "_create_config:"
        new_chat_config_file = open(self.config_file_path, "w+")
        debug_logger.log(f"{fn} at {self.config_file_path}")
        config = dict(started=False, unleashed=False, introduced=False, count=None)
        json.dump(config, new_chat_config_file)
        new_chat_config_file.close()
        return open(self.config_file_path, "r+")

    def _open_config(self) -> TextIOWrapper:
        fn = "_open_config:"
        debug_logger.log(f"{fn} at {self.config_file_path}")
        debug_logger.log(f"isfile(self.config_file_path)={isfile(self.config_file_path)}")
        if not isfile(self.config_file_path):
            return self._create_config()
        return open(self.config_file_path, "r+")

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
        debug_logger.log(f"{fn} chat_history={try_get(chat_history, 0)}")
        return chat_history

    def get_config(self) -> dict:
        return self.config.to_dict()

    def update_config(self, new_config: dict):
        fn = "update_config:"
        debug_logger.log(f"{fn} chat_id={self.chat_id}")
        self.config.update_config(new_config)
        self.config_file.seek(0)
        self.config_file.write(json.dumps(self.config.to_dict()))
        self.config_file.truncate()

    def get_chat_id(self) -> int:
        fn = "get_chat_id:"
        debug_logger.log(f"{fn} chat_id={self.chat_id}")
        return self.chat_id

    def start(self) -> bool:
        fn = "start:"
        self.update_config(dict(started=True, introduced=True))
        started = self.config.started
        introduced = self.config.introduced
        debug_logger.log(f"{fn} started={started} introduced={introduced}")

    def stop(self) -> bool:
        fn = "stop:"
        self.update_config(dict(started=False))
        stopped = not self.config.started
        debug_logger.log(f"{fn} stopped={stopped}")

    def is_started(self) -> bool:
        fn = "is_started:"
        started = self.config.started
        debug_logger.log(f"{fn} {started}")
        return started

    def is_stopped(self) -> bool:
        fn = "is_not_started:"
        stopped = not self.is_started()
        debug_logger.log(f"{fn} {stopped}")
        return stopped

    def introduce(self) -> bool:
        fn = "introduce:"
        self.update_config(dict(introduced=True))
        debug_logger.log(f"{fn} introduced={self.config.introduced}")

    def forget(self) -> bool:
        fn = "forget:"
        self.update_config(dict(introduced=False))
        debug_logger.log(f"{fn} forgotten={not self.config.introduced}")

    def is_introduced(self) -> bool:
        fn = "is_introduced:"
        introduced = self.config.introduced
        debug_logger.log(f"{fn} {introduced}")
        return introduced

    def is_forgotten(self) -> bool:
        fn = "is_forgotten:"
        forgotten = not self.is_introduced()
        debug_logger.log(f"{fn} {forgotten}")
        return forgotten

    def unleash(self, count: int) -> bool:
        fn = "unleash:"
        self.update_config(dict(unleashed=True, count=count))
        unleashed = self.config.unleashed
        self.config.count = count
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")

    def leash(self) -> bool:
        fn = "leash:"
        self.update_config(dict(unleashed=False, count=None))
        leashed = not self.config.unleashed
        count = self.config.count
        debug_logger.log(f"{fn} leashed={leashed} count={count}")

    def is_unleashed(self) -> bool:
        fn = "is_unleashed:"
        unleashed = self.config.unleashed
        count = self.config.count
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")
        return unleashed, count

    def is_leashed(self) -> bool:
        fn = "is_leashed:"
        unleashed, count = self.is_unleashed()
        debug_logger.log(f"{fn} unleashed={unleashed} count={count}")
        return not unleashed, count

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
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        return len(self.tokenize(content))

    def calculate_chat_history_tokens(self) -> int:
        fn = "calculate_chat_history_tokens:"
        total = 0
        for data in self.chat_history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        debug_logger.log(f"{fn} {self.name} token_count={total}")
        return total

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        fn = "update_chat_history:"
        debug_logger.log(fn)
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        # self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1
        self.chat_history_tokens += len(self.tokenize(try_get(chat_message, "content")))

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
        answer = abbot_api.
        answer = requests.
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
