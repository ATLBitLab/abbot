import json
<<<<<<<< HEAD:src/lib/abbot.py
import time
========
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
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

<<<<<<<< HEAD:src/lib/abbot.py
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
========
from io import TextIOWrapper, open
from os.path import abspath, isfile
from bot.exceptions.abbot_exception import try_except

from constants import OPENAI_MODEL
from config import BOT_INTRO, OPENAI_API_KEY, BOT_CHAT_HISTORY_FILEPATH

from lib.logger import debug_logger
from lib.utils import try_get

encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


class Abbot:
    cl = "abbot =>"

>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
<<<<<<<< HEAD:src/lib/abbot.py
        context: str,
        chat_id: int,
========
        chat_id: int = None,
        started: bool = False,
        sent_intro: bool = False,
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id
<<<<<<<< HEAD:src/lib/abbot.py

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
========
        self.started: bool = started
        self.unleashed: bool = started
        self.sent_intro: bool = sent_intro
        self.chat_history_file_path = abspath(BOT_CHAT_HISTORY_FILEPATH)
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_tokens = self.calculate_chat_history_tokens()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()

    def __str__(self) -> str:
<<<<<<<< HEAD:src/lib/abbot.py
        return (
            f"GPT(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"unleashed={self.unleashed}, started={self.started} "
            f"chat_id={self.chat_id}, chat_history_tokens={self.chat_history_tokens})"
========
        fn = "__str__ =>"
        abbot_str = (
            f"Abbot(model={self.model}, name={self.name}, "
            f"handle={self.handle}, unleashed={self.unleashed}, "
            f"started={self.started}, chat_id={self.chat_id}, "
            f"chat_history_token_length={self.chat_history_token_length})"
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
        )
        debug_logger.log(f"{fn} abbot_str={abbot_str}")
        return abbot_str

    def __repr__(self) -> str:
        fn = "__repr__ =>"
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
        fn = "_create_history =>"
        chat_history_file = open(self.chat_history_file_path, "a+")
        chat_history_file.write(json.dumps(self.gpt_system))
        return chat_history_file

    def _open_history(self) -> TextIOWrapper:
        fn = "_open_history =>"
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "a+")

<<<<<<<< HEAD:src/lib/abbot.py
========
    def _close_history(self) -> None:
        fn = "_close_history =>"
        self.chat_history_file.close()

>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
    def _inflate_history(self) -> list:
        fn = "_inflate_history =>"
        chat_history = []
        self.chat_history_file_cursor = self.chat_history_file.tell()
        self.chat_history_file.seek(0)
        for message in self.chat_history_file.readlines():
            if not message:
                continue
            chat_history.append(json.loads(message))
        self.chat_history_file.seek(self.chat_history_file_cursor)
        return chat_history[1:]

<<<<<<<< HEAD:src/lib/abbot.py
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
========
    def status(self) -> (bool, bool):
        fn = "status =>"
        return self.started, self.sent_intro

    def bot_ready(self) -> bool:
        fn = "bot_ready =>"
        return self.started and self.sent_intro

    def intro_sent(self) -> bool:
        fn = "intro_sent =>"
        return self.sent_intro

    def start(self) -> bool:
        fn = "start =>"
        self.started = True
        self._open_history()
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
        return self.started

    def start_command(self) -> bool:
        fn = "start_command =>"
        started = self.start()
        send_intro = self.hello()
        if not started and not send_intro:
            return False
        self._open_history()
        return not self.bot_ready()

    def stop(self) -> bool:
<<<<<<<< HEAD:src/lib/abbot.py
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
========
        fn = "stop =>"
        self.started = False
        return not self.started

    def stop_command(self) -> bool:
        fn = "stop_command =>"
        return not self.stop()

    def hello(self) -> bool:
        fn = "hello =>"
        self.sent_intro = True
        return BOT_INTRO

    def goodbye(self) -> bool:
        fn = "goodbye =>"
        self.sent_intro = False
        return True

    def update_chat_history(self, chat_message: dict(role=str, content=str)) -> None:
        fn = "update_chat_history =>"
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1
        content: str = try_get(chat_message, "content")
        self.chat_history_tokens += len(self.tokenize(content))
        return self.chat_history_tokens

<<<<<<<< HEAD:src/lib/abbot.py
    def tokenize(self, content: str) -> list:
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        return len(self.tokenize(content))

    def calculate_chat_history_tokens(self) -> int:
========
    def chat_completion(self) -> str | Exception:
        fn = "chat_completion =>"
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.chat_history,
        )
        answer = try_get(response, "choices", 0, "message", "content")
        response_dict = dict(role="assistant", content=answer)
        if answer:
            self.update_chat_history(response_dict)
        return answer

    def tokenize(self, content: str) -> list:
        fn = "tokenize =>"
        return encoding.encode(content)

    def calculate_tokens(self, content: str | dict) -> int:
        fn = "calculate_tokens =>"
        return len(self.tokenize(content))

    def calculate_chat_history_tokens(self) -> int:
        fn = "calculate_chat_history_tokens =>"
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
        total = 0
        for data in self.chat_history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    @try_except
<<<<<<<< HEAD:src/lib/abbot.py
    def chat_completion(self) -> str | None:
        messages = [self.gpt_system]
        history = self.chat_history
        if self.chat_history_tokens > 4500:
            index = self.chat_history_len // 2
            history = history[index:]
        messages.extend(history)
========
    def chat_history_completion(self) -> str | None:
        fn = "chat_history_completion =>"
        debug_logger.log(fn)
        chat_history_token_count = self.calculate_chat_history_tokens()
        debug_logger.log(f"{fn} token_count={chat_history_token_count}")
        messages = [self.gpt_system]
        debug_logger.log(f"{fn} messages={messages}")
        messages.extend(self.chat_history)
        debug_logger.log(f"{fn} messages={messages}")
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
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

<<<<<<<< HEAD:src/lib/abbot.py
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
========
    def get_chat_history(self) -> list:
        fn = "get_chat_history =>"
        return self.chat_history
>>>>>>>> 2cb0906bd9d9ef7b14ab50d785b1c383463dcfcb:src/lib/bot/abbot.py
