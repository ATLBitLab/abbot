from cli_args import TEST_MODE

from typing import Dict, List
from dataclasses import dataclass, field

from pymongo import MongoClient
from pymongo.cursor import Cursor
from bson.typings import _DocumentType

from lib.abbot.env import DATABASE_CONNECTION_STRING
from lib.abbot.exceptions.exception import try_except
from lib.logger import error_logger
from lib.utils import try_get

client = MongoClient(host=DATABASE_CONNECTION_STRING)

nostr_db_name = "test_nostr" if TEST_MODE else "nostr"
db_nostr = client.get_database(nostr_db_name)
nostr_channels = db_nostr.get_collection("channel")
nostr_dms = db_nostr.get_collection("dm")

telegram_db_name = "test_telegram" if TEST_MODE else "telegram"
db_telegram = client.get_database(telegram_db_name)
telegram_chats = db_telegram.get_collection("chat")
telegram_dms = db_telegram.get_collection("dm")


class Config:
    def __init__(
        self,
        started=False,
        introduced=False,
        unleashed=False,
        count=None,
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


@dataclass
class NostrChannel:
    id: str
    pubkey: str
    content: str
    sig: str
    config: Config = field(default_factory=Config().to_dict())
    created_at: int = 0000000000
    kind: int = 40
    tags: List[List[str]] = field(default_factory=list)
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class NostrDirectMessage:
    id: str
    sender_pk: str
    receiver_pk: str
    started_at: int = 0000000000
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return self.__dict__

    @try_except
    def validate_direct_messages(self, direct_messages: List[Dict]) -> List[Dict]:
        valid_direct_messages = []
        for direct_message in direct_messages:
            valid_direct_message = NostrDirectMessage(direct_message)
            valid_direct_messages.append(valid_direct_message)
        return valid_direct_messages


class MongoNostr:
    def __init__(self):
        pass

    @try_except
    def validate_doc_for_insert(self, docs: List[Dict], is_channel: bool = True) -> List[Dict]:
        try:
            valid_docs = []
            for doc in docs:
                valid_doc = NostrChannel(doc) if is_channel else NostrDirectMessage(doc)
                valid_docs.append(valid_doc)
            return valid_docs
        except:
            error_logger.log(f"invalid nostr channel, skipping {'channel' if is_channel else 'dm'} {valid_doc}")
            pass

    @try_except
    def insert_channel(self, channel_data: NostrChannel):
        nostr_channels.insert_one(channel_data.__dict__)

    @try_except
    def insert_channels(self, channels: List[NostrChannel]):
        nostr_channels.insert_many(list(map(lambda channel: channel, self.validate_doc_for_insert(channels))))

    @try_except
    def insert_dm(self, direct_message_data: NostrDirectMessage):
        nostr_dms.insert_one(direct_message_data)

    @try_except
    def insert_dms(self, direct_messages: List[NostrDirectMessage]):
        nostr_dms.insert_many(list(map(lambda dm: dm, self.validate_doc_for_insert(direct_messages))))

    @try_except
    def find_channel(self, filter: {}) -> NostrChannel:
        return nostr_channels.find_one(filter)

    @try_except
    def find_channels(self, filter: {}) -> List[NostrChannel]:
        channels = []
        for channel in nostr_channels.find(filter):
            channels.append(channel)
        return channels

    @try_except
    def find_channels_cursor(self, filter: {}) -> Cursor[_DocumentType]:
        return nostr_channels.find(filter)

    @try_except
    def find_dm(self, filter: {}):
        return nostr_dms.find_one(filter)

    @try_except
    def find_dms(self, filter: {}):
        dms = []
        for nostr_dm in nostr_dms.find(filter):
            dms.append(nostr_dm)
        return dms

    @try_except
    def find_dms_cursor(self, filter: {}) -> Cursor[_DocumentType]:
        return nostr_dms.find(filter)

    @try_except
    def get_bot_channel_invite_author_whitelist():
        pass


class MongoTelegram:
    def __init__(self):
        pass
