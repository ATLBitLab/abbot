import json
import PyPDF2
import requests

from typing import AnyStr
from io import TextIOWrapper, open
from os.path import abspath, isfile

from io import BytesIO
from lib.logger import debug_abbot, error_abbot
from lib.utils import deconstruct_error, try_get

from env import OPENAI_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID
from constants import ARW, OPENAI_MODEL

import openai
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model(OPENAI_MODEL)

from langchain.tools import Tool
from langchain.utilities import GoogleSearchAPIWrapper

search = GoogleSearchAPIWrapper(
    google_api_key=GOOGLE_API_KEY, google_cse_id=GOOGLE_CSE_ID
)
tool = Tool(
    name="Google Search",
    description="Search Google for recent results.",
    func=search.run,
)
from bs4 import BeautifulSoup


class Abbots:
    BOTS: dict = dict()

    def __init__(self, abbots: list):
        bots: dict = dict()
        for abbot in abbots:
            name = try_get(abbot, "chat_id")
            bots[name] = abbot
        self.BOTS.update(bots)
        debug_abbot(f"gpt => Abbots => self.BOTS={self.BOTS.keys()}")

    def __str__(self) -> str:
        _str_ = f"\nAbbots(BOTS="
        BOTS = self.BOTS.values()
        for bot in BOTS:
            _str_ += f"{bot.__str__()})\n"
        return f"{_str_.rstrip()})\n"

    def __repr__(self) -> str:
        return f"Abbots(BOTS={self.BOTS})"

    def get_bots(self) -> dict:
        return self.BOTS


class GPT(Abbots):
    def __init__(
        self,
        name: str,
        handle: str,
        personality: str,
        context: str,
        chat_id: int = None,
        started: bool = False,
        count: int = 5,
    ) -> object:
        openai.api_key: str = OPENAI_API_KEY
        self.model: str = OPENAI_MODEL
        self.name: str = name
        self.handle: str = handle
        self.context: str = context
        self.personality: str = personality
        self.gpt_system: dict = dict(role="system", content=personality)
        self.chat_id: str = chat_id
        self.started: bool = started
        self.unleashed: bool = started
        self.count: int = count
        self.chat_history_token_count: int = None

        chat_history_abs_filepath: AnyStr @ abspath = abspath(f"data/gpt/{context}")
        self.chat_history_file_path: str = (
            f"{chat_history_abs_filepath}/{chat_id}.jsonl"
            if chat_id
            else f"{chat_history_abs_filepath}/{context}_abbot.jsonl"
        )
        self.chat_history_file: TextIOWrapper = self._open_history()
        self.chat_history_file_cursor: int = self.chat_history_file.tell()
        self.chat_history: list = self._inflate_history()

    def __str__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, "
            f"handle={self.handle}, context={self.context}, "
            f"chat_id={self.chat_id}, started={self.started}, "
            f"count={self.count})"
        )

    def __repr__(self) -> str:
        return (
            f"GPT(model={self.model}, name={self.name}, handle={self.handle}, "
            f"context={self.context}, personality={self.personality}, "
            f"unleashed={self.unleashed}, started={self.started}, "
            f"count={self.count}, chat_history={self.chat_history[self.count:]})"
        )

    def _create_history(self) -> TextIOWrapper:
        chat_history_file = open(self.chat_history_file_path, "a+")
        chat_history_file.write(f"{json.dumps(self.gpt_system)}\n")
        return chat_history_file

    def _open_history(self) -> TextIOWrapper:
        if not isfile(self.chat_history_file_path):
            return self._create_history()
        return open(self.chat_history_file_path, "a+")

    def _close_history(self) -> None:
        self.chat_history_file.close()

    def _inflate_history(self) -> list:
        content = ""
        chat_history = []
        self.chat_history_file_cursor = self.chat_history_file.tell()
        self.chat_history_file.seek(0)
        for message in self.chat_history_file.readlines():
            if not message:
                continue
            loaded_message = json.loads(message)
            chat_history.append(loaded_message)
            content += try_get(loaded_message, "content")
        self.chat_history_token_count = len(encoding.encode(content))
        self.chat_history_file.seek(self.chat_history_file_cursor)
        return chat_history

    def status(self) -> dict:
        status = dict(
            name=self.name,
            started=self.started,
            unleashed=self.unleashed,
        )
        if not self.chat_id:
            return status
        status.update(dict(chat_id=self.chat_id))
        return status

    def start(self) -> bool | Exception:
        try:
            self.started = True
            self.unleashed = self.started
            self._open_history()
            return self.started
        except Exception as exception:
            error_abbot(f"{self.name} start => exception={exception}")
            raise exception

    def stop(self) -> bool | Exception:
        try:
            self.started = False
            self.unleashed = self.started
            self.chat_history_file.close()
            return self.started
        except Exception as exception:
            error_abbot(f"{self.name} stop => exception={exception}")
            raise exception

    def unleash(self) -> bool:
        self.unleashed = True
        return self.unleashed

    def leash(self) -> bool:
        self.unleashed = False
        return self.unleashed

    def update_chat_history(
        self, chat_message: dict(role=str, content=str)
    ) -> None | Exception:
        try:
            self.chat_history.append(chat_message)
            self.chat_history_file.write(f"{json.dumps(chat_message)}\n")
        except Exception as exception:
            error_abbot(f"{self.name} update_chat_history => exception={exception}")
            raise exception

    def chat_history_completion(self) -> str | Exception:
        try:
            start_index = len(self.chat_history) / 2
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.chat_history[start_index:],
            )
            answer = try_get(response, "choices", 0, "message", "content")
            response_dict = dict(role="assistant", content=answer)
            self.update_chat_history(response_dict)
            return answer
        except Exception as exception:
            error_abbot(f"chat_history_completion => exception={exception}")
            raise exception

    def update_abbots(self, chat_id: str | int, bot: object) -> None | Exception:
        try:
            Abbots.BOTS[chat_id] = bot
            debug_abbot(f"update_abbots => chat_id={chat_id}")
        except Exception as exception:
            error_abbot(f"update_abbots => exception={exception}")
            raise exception

    def get_abbots(self) -> Abbots.BOTS:
        return Abbots.BOTS

    def get_chat_history(self) -> list:
        return self.chat_history

    def scrape_url(self, url: str) -> str:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            print(soup.prettify())
        except Exception as exception:
            cause, traceback, args = deconstruct_error(exception)
            error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
            error_abbot(f"scrape_pdf => Error={exception}, ErrorMessage={error_msg}")
            raise exception

    def internet_search(prompt: str) -> str | Exception:
        try:
            return tool.run(prompt.lower())
        except Exception as exception:
            error_abbot(f"internet_search => exception={exception}")
            raise exception


"""
response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.chat_history[len(self.chat_history) / 2 :],
                functions=internet_search,
                function_call="auto",
            )
internet_search = [
                {
                    "name": "internet_search",
                    "description": "Do an internet search for a given search query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The given search query",
                            },
                        },
                    },
                }
            ]
def chat_completion:
choice = try_get(response, "choices", 0)
            message = try_get(response, "choices", 0, "message")
            if try_get(choice, "finish_reason") == "function_call":
                function_call = try_get(message, "function_call")
                name = try_get(function_call, "name")
                arguments = try_get(function_call, "arguments")
                if name == "internet_search":
                    prompt = self.chat_completion("turn the following user input into a search query for a search engine")
                    answer = self.internet_search()
            else:
                if not function_call:
                    raise Exception(
                        "gpt.chat_history_completion => no answer and no function_call"
                    )
                elif not name or not arguments:
                    raise Exception(
                        "gpt.chat_history_completion => function_call without name or args"
                    )
"""


def scrape_pdf(url: str) -> str | Exception:
    try:
        content = ""
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Response failed {response.status_code}")
        pdf_file = BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page_number in range(len(pdf_reader.pages)):
            pdf_page = pdf_reader.pages[page_number]
            content += pdf_page.extract_text()
        return content
    except Exception as exception:
        cause, traceback, args = deconstruct_error(exception)
        error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
        error_abbot(f"scrape_pdf => Error={exception}, ErrorMessage={error_msg}")
        raise exception


# def internet_search(search_matches, which_abbot: GPT):
#     try:
#         fn = f"search_internet {ARW} "
#         debug_abbot(f"{fn} search_matches={search_matches}")
#         matches_len = len(search_matches)
#         debug_abbot(f"{fn} matches_len={matches_len}")
#         if matches_len > 0:
#             if matches_len == 1:
#                 search_results = which_abbot.internet_search(search_matches[0])
#             else:
#                 search_results = [
#                     which_abbot.internet_search(match) for match in search_matches
#                 ]
#                 search_results = ". ".join(search_results)
#             debug_abbot(f"{fn} search_results={search_results}")
#         return search_results
#     except Exception as exception:
#         cause, traceback, args = deconstruct_error(exception)
#         error_msg = f"args={args}\n" f"cause={cause}\n" f"traceback={traceback}"
#         error_abbot(f"scrape_pdf => Error={exception}, ErrorMessage={error_msg}")
#         raise exception
