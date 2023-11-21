import time
import openai
import tiktoken

from abc import abstractmethod
from bson.typings import _DocumentType
from typing import List, Optional, Dict

from constants import OPENAI_MODEL

from ..db.utils import successful_update_one
from ..utils import error, success, to_dict, try_get
from ..abbot.config import BOT_CORE_SYSTEM
from ..db.mongo import GroupConfig, UpdateResult, mongo_abbot

from ..logger import bot_debug, bot_error
from ..abbot.exceptions.exception import try_except

from ..abbot.env import OPENAI_API_KEY

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


@to_dict
class Abbot(GroupConfig):
    def __init__(self, id: str, bot_type: str):
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.id: str = id
        self.bot_type: str = bot_type
        self.context: Dict = self.set_context()
        self.history: List = [{"role": "system", "content": BOT_CORE_SYSTEM}, *self.context.get("history", None)]
        if self.history == None:
            raise Exception(f"self.history is none = {self.context}")
        self.history_len: int = len(self.history)
        self.history_tokens: int = self.calculate_history_tokens()
        self.config: GroupConfig = GroupConfig()

    def __str__(self) -> str:
        return self.__str__()

    def __repr__(self) -> str:
        return self.__repr__()

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @try_except
    def set_context(self) -> Optional[_DocumentType]:
        if self.bot_type == "dm":
            return mongo_abbot.find_one_dm({"id": self.id})
        else:
            return mongo_abbot.find_one_channel({"id": self.id})

    @try_except
    def get_config(self) -> Dict:
        return self.config.to_dict()

    @try_except
    def update_config(self, new_config: Dict):
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
    def get_messages(self) -> List:
        return self.context.get("messages", None)

    @try_except
    def tokenize(self, content: str) -> list:
        return encoding.encode(content)

    @try_except
    def calculate_tokens(self, content: str) -> int:
        return len(self.tokenize(content))

    @try_except
    def calculate_history_tokens(self) -> int:
        total = 0
        for data in self.history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    @try_except
    def update_db(self, update: Dict) -> Dict | UpdateResult:
        result: UpdateResult = mongo_abbot.update_one(self.bot_type, {"id": self.id}, update)
        if not successful_update_one(result):
            bot_error.log(f"update_db failed: {update}")
            return error("update_db => update_one_channel failed")
        return success(try_get(result, "upserted_id"))

    @try_except
    def update_history(self, update: Dict[str, str]) -> int:
        if not update:
            return
        self.history.append(update)
        result: UpdateResult = mongo_abbot.update_one_history(
            self.bot_type, {"id": self.id}, {"$push": {"history": update}}
        )
        if not successful_update_one(result):
            bot_error.log(f"update_history failed: {update}")
            return error("update_history => update_one_channel failed")
        self.history_len += 1
        self.history_tokens += len(self.tokenize(try_get(update, "content")))
        return success(try_get(result, "upserted_id"))

    @try_except
    def chat_completion(self) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        self.update_history({"role": "assistant", "content": answer})
        return answer
