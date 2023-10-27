from sys import argv

ARGS = argv[1:]
TEST_MODE = "-t" in ARGS or "--test" in ARGS

from typing import Dict, List
from dataclasses import dataclass, field, fields

from pymongo import MongoClient
from pymongo.cursor import Cursor
from bson.typings import _DocumentType

from lib.abbot.env import DATABASE_CONNECTION_STRING
from lib.logger import error_logger


@dataclass
class TelegramChannel:
    pass


@dataclass
class TelegramDirectMessage:
    pass


@dataclass
class NostrChannel:
    id: str = field(default="", metadata={"required": True})
    pubkey: str = field(default="", metadata={"required": True})
    created_at: int = field(default=0000000000, metadata={"required": True})
    kind: int = field(default=40, metadata={"required": True})
    tags: List[List[str]] = field(default_factory=list, metadata={"required": True})
    content: str = field(default="", metadata={"required": True})
    sig: str = field(default="", metadata={"required": True})
    messages: List[Dict] = field(default_factory=list, metadata={"required": False})
    history: List[Dict] = field(default_factory=list, metadata={"required": False})

    def required_instance_vars(self):
        return {f.name for f in fields(self) if f.metadata.get("required", True)}

    def to_dict(self):
        return self.__dict__

    def validate(channels: List[dict]):
        valid_nostr_channels = []
        for channel in channels:
            valid_nostr_channel = NostrChannel(channel)
            valid_nostr_channels.append(valid_nostr_channel)
        return valid_nostr_channels


@dataclass
class NostrDirectMessage:
    id: str = ""
    sender_pk: str = ""
    started_at: int = 0000000000
    receiver_pk: str = ""
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def required_instance_vars(self):
        return {f.name for f in fields(self) if f.metadata.get("required", True)}

    def to_dict(self):
        return self.__dict__

    def is_valid(self, direct_message: dict) -> bool:
        return set(direct_message.keys()).difference(self.required_instance_vars())

    def validate(direct_messages: List[dict]):
        valid_direct_messages = []
        for direct_message in direct_messages:
            nostr_direct_message = NostrDirectMessage()
            if nostr_direct_message.is_valid(direct_message):
                valid_direct_messages.append(direct_message)
        return valid_direct_messages


client = MongoClient(host=DATABASE_CONNECTION_STRING)


class AbbotDatabase:
    def __init__(self, db):
        self.db_name = f"test_{db}" if TEST_MODE else db
        self.db = client.get_database(self.db_name)
        self.channel_collection = self.db.get_collection("channel")
        self.dm_collection = self.db.get_collection("dm")

    def insert_channel(self, channel_data: NostrChannel):
        self.channel_collection.insert_one(channel_data.to_dict())

    def insert_channels(self, channels: List[NostrChannel]):
        self.channel_collection.insert_many(list(map(lambda channel: channel.to_dict(), channels)))

    def insert_dm(self, direct_message_data: NostrDirectMessage):
        self.dm_collection.insert_one(direct_message_data)

    def insert_dms(self, dms: List[NostrDirectMessage]):
        self.dm_collection.insert_many(list(map(lambda dm: dm.to_dict(), dms)))

    def find_channel(self, filter: {}):
        return self.channel_collection.find_one(filter)

    def find_channels(self, filter: {}):
        channels = []
        for channel in self.channel_collection.find(filter):
            channels.append(channel)
        return channels

    def find_dm(self, filter: {}):
        return self.dm_collection.find_one(filter)

    def find_dms(self, filter: {}):
        dms = []
        for nostr_dm in self.dm_collection.find(filter):
            dms.append(nostr_dm)
        return dms

    def find_dms_cursor(self, filter: {}) -> Cursor[_DocumentType]:
        return self.dm_collection.find(filter)

    def find_channels_cursor(self, filter: {}) -> Cursor[_DocumentType]:
        return self.channel_collection.find(filter)


nostr_db = AbbotDatabase("nostr")
telegram_db = AbbotDatabase("telegram")
