from ast import Dict
import time
import openai
import tiktoken

from typing import List
from abc import abstractmethod

from lib.db.utils import successful_update_one

from ..utils import error, to_dict, try_get
from lib.abbot.config import BOT_CORE_SYSTEM
from lib.db.mongo import (
    GroupConfig,
    MongoNostr,
    UpdateResult,
    nostr_dms,
    nostr_channels,
)

from lib.logger import bot_debug, bot_error
from lib.abbot.exceptions.exception import try_except

from constants import OPENAI_MODEL
from lib.abbot.env import OPENAI_API_KEY

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
mongo_nostr = MongoNostr()


@to_dict
class Abbot(GroupConfig):
    def __init__(self, id: str, bot_type: str):
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.id: str = id
        self.bot_type: str = bot_type
        self.channel_or_dm: Dict = self.determine_and_set_channel_or_dm()
        self.history: List = [{"role": "system", "content": BOT_CORE_SYSTEM}, *self.channel_or_dm.get("history", None)]
        if self.history == None:
            raise Exception(f"self.history is none {self.channel_or_dm}")
        self.history_len = len(self.history)
        self.history_tokens = self.calculate_history_tokens()
        self.config: GroupConfig = GroupConfig()

    def determine_and_set_channel_or_dm(self):
        if self.bot_type == "dm":
            channel_or_dm = mongo_nostr.find_one_dm({"id": self.id})
        else:
            channel_or_dm = mongo_nostr.find_one_channel({"id": self.id})
        if not channel_or_dm:
            raise Exception("not channel_or_dm")

    def calculate_history_tokens(self) -> int:
        total = 0
        for data in self.history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    def __str__(self) -> str:
        return self.__str__()

    def __repr__(self) -> str:
        return self.__repr__()

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @try_except
    def determine_and_set_channel_or_dm(self):
        if self.bot_type == "dm":
            channel_or_dm = mongo_nostr.find_one_dm({"id": self.id})
        else:
            channel_or_dm = mongo_nostr.find_one_channel({"id": self.id})
        if not channel_or_dm:
            raise Exception("not channel_or_dm")

    @try_except
    def get_config(self) -> dict:
        return self.config.to_dict()

    @try_except
    def update_config(self, new_config: dict):
        self.config.update_config(new_config)

    @try_except
    def start(self) -> bool:
        self.update_config(dict(started=True, introduced=True))
        return self.config.started

    @try_except
    def stop(self) -> bool:
        self.update_config(dict(started=False))
        return not self.config.started

    @try_except
    def introduce(self) -> bool:
        self.update_config(dict(introduced=True))
        return self.config.introduced

    @try_except
    def forget(self) -> bool:
        self.update_config(dict(introduced=False))
        return not self.config.introduced

    @try_except
    def is_started(self) -> bool:
        return self.config.started

    @try_except
    def is_stopped(self) -> bool:
        return not self.is_started()

    @try_except
    def is_introduced(self) -> bool:
        return self.config.introduced

    @try_except
    def is_forgotten(self) -> bool:
        return not self.is_introduced()

    @try_except
    def unleash(self, count: int) -> bool:
        self.update_config(dict(unleashed=True, count=count))
        self.config.unleashed
        self.config.count = count

    @try_except
    def leash(self) -> bool:
        self.update_config(dict(unleashed=False, count=None))
        not self.config.unleashed
        self.config.count

    @try_except
    def is_unleashed(self) -> bool:
        return self.config.unleashed, self.config.count

    @try_except
    def is_leashed(self) -> bool:
        unleashed, count = self.is_unleashed()
        return not unleashed, count

    @try_except
    def sleep(self, t: int) -> str:
        time.sleep(t)
        return True

    @try_except
    def get_history(self) -> list:
        return self.history

    @try_except
    def get_messages(self) -> list:
        return self.channel_or_dm["messages"]

    @try_except
    def tokenize(self, content: str) -> list:
        return encoding.encode(content)

    @try_except
    def calculate_tokens(self, content: str | dict) -> int:
        return len(self.tokenize(content))

    @try_except
    def calculate_history_tokens(self) -> int:
        total = 0
        for data in self.history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    @try_except
    def update_history(self, history_message: dict) -> None:
        if not history_message:
            return
        self.history.append(history_message)
        result: UpdateResult = mongo_nostr.update_one_channel({"id": self.id}, {"$push": {"history": history_message}})
        if not successful_update_one(result):
            bot_error.log(f"update_history failed: {history_message}")
            return error("update_history => update_one_channel failed")
        self.history_len += 1
        self.history_tokens += len(self.tokenize(try_get(history_message, "content")))
        return self.history_tokens

    @try_except
    def chat_completion(self) -> str | None:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        self.update_history({"role": "assistant", "content": answer})
        return answer
