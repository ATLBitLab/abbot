from sys import argv

ARGS = argv[1:]
TEST_MODE = "-t" in ARGS or "--test" in ARGS

from typing import Dict, List
from dataclasses import dataclass, field

from pymongo import MongoClient
from lib.abbot.env import DATABASE_CONNECTION_STRING

client = MongoClient(host=DATABASE_CONNECTION_STRING)

nostr_db_name = "test_nostr" if TEST_MODE else "nostr"
db_nostr = client.get_database(nostr_db_name)
nostr_channels = db_nostr.get_collection("channel")
nostr_dms = db_nostr.get_collection("dm")

telegram_db_name = "test_telegram" if TEST_MODE else "telegram"
db_telegram = client.get_database(telegram_db_name)
telegram_chats = db_telegram.get_collection("chat")
telegram_dms = db_telegram.get_collection("dm")


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


@dataclass
class NostrDirectMessage:
    id: str = ""
    sender_pk: str = ""
    started_at: int = 0000000000
    receiver_pk: str = ""
    messages: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)


class MongoNostr:
    dms = []
    channels = []

    def __init__(self):
        pass

    def insert_channel(self, channel_data: NostrChannel):
        nostr_channels.insert_one(channel_data.__dict__)

    def insert_channels(self, channels: List[NostrChannel]):
        nostr_channels.insert_many(channels)

    def insert_dm(self, direct_message_data: NostrDirectMessage):
        nostr_dms.insert_one(direct_message_data)

    def insert_dms(self, direct_messages: List[NostrDirectMessage]):
        nostr_dms.insert_many(direct_messages)

    def find_channel(self, filter: {}):
        return nostr_channels.find_one(filter)

    def find_channels(self, filter: {}):
        for channel in nostr_channels.find(filter):
            self.channels.append(channel)
        return self.channels

    def find_dm(self, filter: {}):
        return nostr_dms.find_one(filter)

    def find_dms(self, filter: {}):
        for nostr_dm in nostr_dms.find(filter):
            self.dms.append(nostr_dm)
        return self.dms


class AbbotMongoTelegram:
    def __init__(self):
        pass
