import time
import tiktoken

from openai import OpenAI

from typing import List, Dict
from abc import abstractmethod
from bson.typings import _DocumentType
from typing import List, Optional, Dict

from traitlets import default

from constants import OPENAI_MODEL

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


@to_dict
class Abbot(GroupConfig):
    from lib.abbot.env import OPENAI_API_KEY

    client: OpenAI = OpenAI(api_key=OPENAI_API_KEY)

    def __init__(self, id: str, bot_type: str):
        self.model: str = OPENAI_MODEL
        self.id: str = id
        self.bot_type: str = bot_type
        self.model: str = OPENAI_MODEL
        self.history: List = [{"role": "system", "content": BOT_CORE_SYSTEM}, *history]
        self.history_len: int = len(self.history)
        self.history_tokens: int = self.calculate_history_tokens()
        self.config: GroupConfig = GroupConfig() if self.bot_type != "dm" else None

    def __str__(self) -> str:
        return f"Abbot(model={self.model}, id={self.id}, bot_type={self.bot_type}, history_len={self.history_len}, history_tokens={self.history_tokens}, config={self.config})"

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    def get_config(self) -> Dict:
        return self.config.to_dict()

    def update_config(self, new_config: Dict):
        self.config.update_config(new_config)

    def start(self) -> bool:
        self.update_config(dict(started=True, introduced=True))
        return self.config.started

    def stop(self) -> bool:
        self.update_config(dict(started=False))
        return not self.config.started

    def introduce(self) -> bool:
        self.update_config(dict(introduced=True))
        return self.config.introduced

    def forget(self) -> bool:
        self.update_config(dict(introduced=False))
        return not self.config.introduced

    def is_started(self) -> bool:
        return self.config.started

    def is_stopped(self) -> bool:
        return not self.is_started()

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

    def calculate_tokens(self, content: str) -> int:
        return len(self.tokenize(content))

    def calculate_history_tokens(self) -> int:
        total = 0
        for data in self.history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    def update_db(self, update: Dict) -> Dict | UpdateResult:
        result: UpdateResult = mongo_abbot.update_one(self.bot_type, {"id": self.id}, update)
        if not successful_update_one(result):
            bot_error.log(f"update_db failed: {update}")
            return error("update_db => update_one_channel failed")
        return success(try_get(result, "upserted_id"))

    @try_except
    def chat_completion(self) -> str | None:
        response = self.client.completions.create(
            model=self.model,
            messages=self.history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        self.history.append({"role": "assistant", "content": answer})
        self.update_history_meta(answer)
        bot_debug.log(__name__, f"chat_completion => response={response}")
        if not successful(response):
            bot_error.log(__name__, f"chat_completion => response={response}")
        return answer
