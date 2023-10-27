from sys import argv

ARGS = argv[1:]
TEST_MODE = "-t" in ARGS or "--test" in ARGS

from typing import Dict, List
from dataclasses import dataclass, field

from pymongo import MongoClient
from pymongo.cursor import Cursor
from bson.typings import _DocumentType

from lib.abbot.env import DATABASE_CONNECTION_STRING
from lib.logger import error_logger


@dataclass
class NostrChannel:
    id: str = ""
    pubkey: str = ""
    created_at: int = 0000000000
    kind: int = 40
    tags: List[List[str]] = ""
    content: str = ""
    sig: str = ""
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__


@dataclass
class NostrDM:
    id: str = ""
    sender_pk: str = ""
    started_at: int = 0000000000
    receiver_pk: str = ""
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__


def validate_NostrChannel_data(channels: List[dict]):
    try:
        valid_nostr_channels = []
        for channel in channels:
            valid_nostr_channel = NostrChannel(channel)
            valid_nostr_channels.append(valid_nostr_channel)
        return valid_nostr_channels
    except:
        error_logger.log(f"invalid nostr channel data object, skipping: {channel}")
        pass


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

    def insert_dm(self, direct_message_data: NostrDM):
        self.dm_collection.insert_one(direct_message_data)

    def insert_dms(self, dms: List[NostrDM]):
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
