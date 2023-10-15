import json
import traceback
from io import TextIOWrapper, open
from os.path import abspath, isfile

from bot_constants import OPENAI_MODEL
from lib.bot.config import BOT_INTRO, OPENAI_API_KEY, BOT_CHAT_HISTORY_FILEPATH

from lib.logger import debug_logger, error_logger
from lib.utils import try_get

from lib.exceptions import AbbitException, try_except
import openai
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


class Abbit:
    cl = "Abbit =>"

    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        chat_id: int = None,
        started: bool = False,
        sent_intro: bool = False,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id
        self.started: bool = started
        self.unleashed: bool = started
        self.sent_intro: bool = sent_intro
        self.chat_history_file_path = abspath(BOT_CHAT_HISTORY_FILEPATH)
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()
        self.chat_history: list = self._inflate_history()
        self.chat_history_len = len(self.chat_history)
        self.chat_history_token_length = self.calculate_chat_history_tokens()

    def __str__(self) -> str:
        fn = "__str__ =>"
        abbit_str = (
            f"Abbit(model={self.model}, name={self.name}, "
            f"handle={self.handle}, unleashed={self.unleashed}, "
            f"started={self.started}, chat_id={self.chat_id}, "
            f"chat_history_token_length={self.chat_history_token_length})"
        )
        debug_logger.log(f"{fn} abbit_str={abbit_str}")
        return abbit_str

    def __repr__(self) -> str:
        fn = "__repr__ =>"
        abbit_repr = (
            f"Abbit(model={self.model}, name={self.name}, "
            f"handle={self.handle}, personality={self.personality}, "
            f"chat_history={self.chat_history}, unleashed={self.unleashed}, started={self.started})"
        )
        debug_logger.log(f"{fn} abbit_repr={abbit_repr}")
        return abbit_repr

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

    def _close_history(self) -> None:
        fn = "_close_history =>"
        self.chat_history_file.close()

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
        return chat_history

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
        fn = "stop =>"
        self.started = False
        self.chat_history_file.close()
        return not self.started

    def stop_command(self) -> bool:
        fn = "stop_command =>"
        stopped = self.stop()
        if not stopped:
            raise Exception(f"Fail: started={stopped}")
        return not stopped

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
        if not chat_message:
            return
        self.chat_history.append(chat_message)
        self.chat_history_file.write("\n" + json.dumps(chat_message))
        self.chat_history_len += 1

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
        total = 0
        for data in self.chat_history:
            content = try_get(data, "content")
            total += self.calculate_tokens(content)
        return total

    @try_except
    def chat_history_completion(self) -> str | None:
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

    # def chat_history_completion(self) -> str | Exception:
    #     fn = "chat_history_completion =>"
    #     chat_context = self.chat_history
    #     chat_history_token_count = self.calculate_chat_history_tokens()
    #     debug_logger.log(f"{fn} token_count={chat_history_token_count}")
    #     if chat_history_token_count > 5000:
    #         reverse_chat_history = [self.personality, *self.chat_history[::-1]]
    #         total = 0
    #         index = 0
    #         shortened_history = [self.personality]
    #         for message_dict in reverse_chat_history:
    #             content = try_get(message_dict, "content")
    #             shortened_history.insert(message_dict)
    #             total += self.calculate_tokens(content)
    #             index += 1
    #             if total >= 2500:
    #                 chat_context = shortened_history
    #                 break
    #     response = openai.ChatCompletion.create(
    #         model=self.model,
    #         messages=chat_context,
    #     )
    #     answer = try_get(response, "choices", 0, "message", "content")
    #     response_dict = dict(role="assistant", content=answer)
    #     self.update_chat_history(response_dict)
    #     return answer

    def get_chat_history(self) -> list:
        fn = "get_chat_history =>"
        return self.chat_history
