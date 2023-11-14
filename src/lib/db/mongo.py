from abc import ABC, abstractmethod
from cli_args import TEST_MODE
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from nostr_sdk import Event

from pymongo import MongoClient
from pymongo.cursor import Cursor
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult

from bson.typings import _DocumentType

from lib.logger import bot_error
from lib.utils import to_dict, error
from lib.abbot.env import DATABASE_CONNECTION_STRING
from lib.db.utils import (
    decorator_successful_insert_one,
    decorator_successful_insert_many,
    decorator_successful_update,
)
from lib.abbot.exceptions.exception import try_except

client = MongoClient(host=DATABASE_CONNECTION_STRING)
nostr_db_name = "test_nostr" if TEST_MODE else "nostr"
db_nostr = client.get_database(nostr_db_name)
nostr_channels = db_nostr.get_collection("channel")
nostr_dms = db_nostr.get_collection("dm")

telegram_db_name = "test_telegram" if TEST_MODE else "telegram"
db_telegram = client.get_database(telegram_db_name)
telegram_chats = db_telegram.get_collection("chat")
telegram_dms = db_telegram.get_collection("dm")


@to_dict
class AbbotConfig:
    def __init__(self, started=False, introduced=False, unleashed=False, count=None, author_whitelist=[]):
        self.started: bool = started
        self.introduced: bool = introduced
        self.unleashed: bool = unleashed
        self.count: int = count
        self.author_whitelist: List = author_whitelist

    @abstractmethod
    def to_dict(self):
        pass

    def update_config(self, data: dict):
        config_dict = self.to_dict()
        config_dict.update(data)
        return self


@to_dict
@dataclass
class NostrEvent:
    kind: int
    id: str = ""
    pubkey: str = ""
    created_at: int = 0000000000
    content: str = ""
    sig: str = ""
    tags: List = field(default_factory=list)

    @abstractmethod
    def to_dict(self):
        pass


# Mongo Nostr Channel doc structure
@to_dict
@dataclass
class MongoNostrChannel(NostrEvent):
    _id: Optional[str] = NostrEvent.id
    id: str = NostrEvent.id
    kind: int = NostrEvent.kind
    pubkey: str = NostrEvent.pubkey
    created_at: int = NostrEvent.created_at
    content: str = NostrEvent.content
    sig: str = NostrEvent.sig
    tags: List = NostrEvent.tags
    config: AbbotConfig = AbbotConfig()
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    """
    history
        description: a list of dictionaries
        purpose: used in open AI chatCompletion API call, preformatted list containing channel history / context
        example:
            history = [
                dict(role="system", content="this is the system prompt as defined in data/config.json BOT_CORE_SYSTEM"),
                dict(role="user", content="this is a user message"),
                dict(role="assistant", content="this is the response from abbot/gpt")
            ]
    """


@to_dict
@dataclass
class MongoNostrDirectMessage(NostrEvent):
    _id: Optional[str] = ""
    id: str = NostrEvent.id
    pubkey: str = NostrEvent.pubkey
    created_at: int = NostrEvent.created_at
    content: str = NostrEvent.content
    sig: str = NostrEvent.sig
    tags: List = NostrEvent.tags
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    @abstractmethod
    def to_dict(self) -> Dict:
        pass

    """
    @try_except
    def validate_insert_dms(self, dms: List[Dict]) -> List[Dict]:
        try:
            valid_dms: List[Dict] = []
            for dm_dict in dms:
                dm_doc: MongoNostrDirectMessage = MongoNostrDirectMessage(dm_dict)
                _id: NostrEvent = dm_doc.nostr_event.id
                valid_doc = MongoNostrDirectMessage(**{"_id": _id, **dm_doc})
                valid_dms.append(valid_doc)
            return valid_dms
        except:
            bot_error.log(f"invalid mongo doc structure, skipping {dm_dict}")
            pass

    @try_except
    def validate_insert_dm(self, doc: Dict, is_channel: bool = True) -> List[Dict]:
        try:
            doc: MongoNostrChannel | MongoNostrDirectMessage = doc
            nostr_event: NostrEvent = doc.nostr_event
            new_doc = {"_id": nostr_event.id, **doc}
            return MongoNostrChannel(**new_doc) if is_channel else MongoNostrDirectMessage(**new_doc)
        except:
            bot_error.log(f"invalid nostr channel, skipping {'channel' if is_channel else 'dm'} {valid_doc}")
            pass
"""


@to_dict
class MongoNostr:
    def __init__(self):
        pass

    @try_except
    @decorator_successful_insert_one
    def insert_one_channel(self, channel: Dict) -> InsertOneResult:
        return nostr_channels.insert_one(channel)

    @try_except
    @decorator_successful_update
    def update_one_channel(self, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        return nostr_channels.update_one(filter, {"$set": {**update}}, upsert)

    @try_except
    def find_one_channel(self, filter: {}) -> Optional[_DocumentType]:
        return nostr_channels.find_one(filter)

    @try_except
    @decorator_successful_insert_many
    def insert_many_channels(self, channels: List[Dict]) -> InsertManyResult:
        return nostr_channels.insert_many(channels)

    @try_except
    def find_channels(self, filter: {}) -> List[Dict]:
        return [channel for channel in nostr_channels.find(filter)]

    @try_except
    def find_channels_cursor(self, filter: {}) -> Cursor:
        return nostr_channels.find(filter)

    @try_except
    def insert_one_dm(self, direct_message: Dict) -> InsertOneResult:
        return nostr_dms.insert_one(direct_message)

    @try_except
    @decorator_successful_insert_many
    def insert_many_dms(self, direct_messages: List[Dict]) -> InsertManyResult:
        return nostr_dms.insert_many(direct_messages)

    @try_except
    @decorator_successful_update
    def update_one_dm(self, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        return nostr_dms.update_one(filter, {"$set": {**update}}, upsert)

    @try_except
    def find_one_dm(self, filter: {}) -> Optional[Dict]:
        return nostr_dms.find_one(filter)

    @try_except
    def find_dms(self, filter: {}) -> List[Dict]:
        return [dm for dm in nostr_dms.find(filter)]

    @try_except
    def find_dms_cursor(self, filter: {}) -> Cursor:
        return nostr_dms.find(filter)

    @try_except
    def get_abbot_config(self, id: str) -> Optional[Dict]:
        channel_doc = self.find_one_channel({"id": id})
        if channel_doc == None:
            return error("Channel does not exist")
        return MongoNostrChannel(**channel_doc).config

    @try_except
    def get_bot_channel_invite_author_whitelist(self):
        pass


@to_dict
class MongoTelegram:
    def __init__(self):
        pass
