import time
import tiktoken
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletionChunk
from abc import abstractmethod
from typing import List, Dict

from constants import OPENAI_MODEL
from ..db.utils import successful_update_one
from ..abbot.config import BOT_SYSTEM_CORE_BLIXT, BOT_SYSTEM_OBJECT_GROUPS
from ..utils import error, success, to_dict, try_get
from ..db.mongo import GroupConfig, UpdateResult, mongo_abbot

from ..logger import debug_bot, error_bot

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
FILE_NAME = __name__


@to_dict
class Abbot(GroupConfig):
    from ..abbot.env import OPENAI_API_KEY, OPENAI_ORG_ID

    client: OpenAI = OpenAI(organization=OPENAI_ORG_ID, api_key=OPENAI_API_KEY)

    def __init__(self, id: str, bot_type: str, history: List):
        log_name: str = f"{__name__}: Abbot.__init__():"
        debug_bot.log(log_name, f"history={history}")
        self.id: str = id
        self.bot_type: str = bot_type
        self.history: List = history
        self.history_len: int = len(history)
        self.history_tokens: int = self.calculate_history_tokens(history)
        if bot_type == "group":
            self.config: GroupConfig = GroupConfig()

    def __str__(self) -> str:
        return f"Abbot(model={OPENAI_MODEL}, id={self.id}, bot_type={self.bot_type}, history_len={self.history_len}, history_tokens={self.history_tokens}, config={self.config})"

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    def get_config(self) -> Dict:
        return self.config.to_dict()

    def get_history(self) -> List:
        return self.history

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
        return encoding.encode(content, allowed_special="all")

    def calculate_tokens(self, content: str) -> int:
        return len(self.tokenize(content))

    def calculate_history_tokens(self, history=None) -> int:
        log_name: str = f"{FILE_NAME}: calculate_history_tokens"
        debug_bot.log(log_name, f"history={history}")
        total = 0
        if not history:
            history = self.history
        for data in history:
            content = try_get(data, "content")
            if not content:
                continue
            total += self.calculate_tokens(content)
        return total

    def update_db(self, update: Dict) -> Dict | UpdateResult:
        log_name: str = f"{FILE_NAME}: calculate_history_tokens"
        result: UpdateResult = mongo_abbot.update_one(self.bot_type, {"id": self.id}, update)
        if not successful_update_one(result):
            error_bot.log(log_name, f"update_db failed: {update}")
            return error("update_db => update_one_channel failed")
        upsert_id = try_get(result, "upserted_id")
        return success(upsert_id)

    def update_history_tokens(self, content: str) -> int:
        self.history_len += 1
        self.history_tokens += len(self.tokenize(content))

    def update_history(self, update: Dict) -> None:
        self.history.append(update)
        content = try_get(update, "content")
        if not content:
            return
        self.update_history_tokens(content)

    def chat_completion(self, chat_title: str | None = None) -> str:
        log_name: str = f"{FILE_NAME}: chat_completion"
        messages_history = self.history
        if self.history_tokens >= 90000:
            messages_history = self.history[self.history_len - 500 : self.history_len]
            if chat_title and "blixt" in chat_title.lower():
                messages_history = [BOT_SYSTEM_CORE_BLIXT, *messages_history]
            else:
                messages_history = [BOT_SYSTEM_OBJECT_GROUPS, *messages_history]
        response: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
            messages=messages_history, model=OPENAI_MODEL
        )
        answer = try_get(response, "choices", 0, "message", "content")
        input_tokens = try_get(response, "usage", "prompt_tokens")
        output_tokens = try_get(response, "usage", "completion_tokens")
        total_tokens = try_get(response, "usage", "total_tokens")
        self.history_tokens += total_tokens
        assistant_update = {"role": "assistant", "content": answer}
        self.update_history(assistant_update)
        if not answer:
            debug_bot.log(log_name, f"chat_completion response={response}")
            error_bot.log(log_name, f"chat_completion => answer={answer}")
            error(response)
        return answer, input_tokens, output_tokens, total_tokens
