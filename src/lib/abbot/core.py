import json
import time
import openai
import tiktoken
import traceback
from typing import AnyStr, List

from lib.db.mongo import Config, MongoNostr, NostrChannel
from ..utils import try_get
from io import TextIOWrapper, open
from os.path import abspath, isfile

from lib.logger import debug_logger, error_logger
from lib.abbot.exceptions.exception import try_except

from constants import OPENAI_MODEL
from lib.abbot.env import OPENAI_API_KEY

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
mongo_nostr = MongoNostr()


def handle_exception(fn: str, e: Exception):
    error_logger.log(f"{fn} exception:\n{e}")
    traceback.print_exc()
    tb = traceback.format_exc()
    error_logger.log(f"{fn} traceback:\n{tb}")


class Bots:
    cl: str = "Bots:"
    abbots: dict = dict()

    def __init__(self, bots: list):
        for bot in bots:
            name = try_get(bot, "id")
            self.abbots[name] = bot

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

    def update_abbots(self, id: str | int, bot: object) -> None:
        self.abbots[id] = bot


class Abbot(Config, Bots):
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        id: int,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.id: str = id
        self.channel: NostrChannel = mongo_nostr.find_channel({"id": id})
        self.config = Config(self.channel)
        self.history: List = self.channel.history
        self.history_len = len(self.history)
        self.history_tokens = self.calculate_history_tokens()

    def __str__(self) -> str:
        return (
            f"Abbot(model={self.model}, name={self.name}, handle={self.handle}, "
            f"id={self.id}, history_tokens={self.history_tokens} "
            f"started={self.config.started}, unleashed={self.config.unleashed})"
        )

    def __repr__(self) -> str:
        return (
            f"Abbot(id={self.id}, name={self.name}, "
            f"handle={self.handle}, personality={self.personality}, "
            f"history_len={self.history_len}, history_tokens={self.history_tokens}"
            f"self.config={self.config})"
        )

    def to_dict(self) -> dict:
        return self.__dict__

    def get_config(self) -> dict:
        return self.config.to_dict()

    def update_config(self, new_config: dict):
        self.config.update_config(new_config)

    def get_id(self) -> int:
        return self.id

    def start(self) -> bool:
        self.update_config(dict(started=True, introduced=True))
        self.config.started
        self.config.introduced

    def stop(self) -> bool:
        self.update_config(dict(started=False))
        not self.config.started

    def is_started(self) -> bool:
        started = self.config.started
        return started

    def is_stopped(self) -> bool:
        return not self.is_started()

    def introduce(self) -> bool:
        self.update_config(dict(introduced=True))

    def forget(self) -> bool:
        self.update_config(dict(introduced=False))

    def is_introduced(self) -> bool:
        return self.config.introduced

    def is_forgotten(self) -> bool:
        return not self.is_introduced()

    def unleash(self, count: int) -> bool:
        self.update_config(dict(unleashed=True, count=count))
        self.config.unleashed
        self.config.count = count

    def leash(self) -> bool:
        self.update_config(dict(unleashed=False, count=None))
        not self.config.unleashed
        self.config.count

    def is_unleashed(self) -> bool:
        return self.config.unleashed, self.config.count

    def is_leashed(self) -> bool:
        unleashed, count = self.is_unleashed()
        return not unleashed, count

    def sleep(self, t: int) -> str:
        time.sleep(t)
        return True

    def get_history(self) -> list:
        return self.history

    def tokenize(self, content: str) -> list:
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        return len(self.tokenize(content))

    def calculate_history_tokens(self) -> int:
        total = 0
        for data in self.history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    def update_history(self, chat_message: dict) -> None:
        if not chat_message:
            return
        self.history.append(chat_message)
        # TODO: update mongo
        self.history_len += 1
        self.history_tokens += len(self.tokenize(try_get(chat_message, "content")))
        return self.history_tokens

    @try_except
    def chat_completion(self) -> str | None:
        messages = [self.gpt_system]
        history = self.history
        if self.history_tokens > 5000:
            index = self.history_len // 2
            history = history[index:]
        messages.extend(history)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        response_dict = dict(role="assistant", content=answer)
        self.update_history(response_dict)
        return answer

    def update_abbots(self, id: str | int, bot: object) -> None:
        Bots.abbots[id] = bot

    def get_abbots(self) -> Bots.abbots:
        return Bots.abbots

    def abbots_to_dict(self):
        return Bots.__dict__
