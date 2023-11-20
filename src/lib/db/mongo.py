from abc import abstractmethod
from cli_args import TEST_MODE, DEV_MODE
from typing import Dict, List, Optional

from nostr_sdk import PublicKey, EventId, Event
from telegram import Chat, Message

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult

from bson.typings import _DocumentType

from lib.logger import bot_error, bot_debug
from lib.utils import to_dict, error, try_get
from lib.abbot.env import DATABASE_CONNECTION_STRING
from lib.abbot.exceptions.exception import try_except

client = MongoClient(host=DATABASE_CONNECTION_STRING)

nostr_db_name = "test_nostr" if TEST_MODE else "nostr"
db_nostr = client.get_database(nostr_db_name)
nostr_channels = db_nostr.get_collection("channels")
bot_channel_invites = db_nostr.get_collection("channel_invites")
nostr_dms = db_nostr.get_collection("dms")

telegram_db_name = "test_telegram" if TEST_MODE else "telegram"
db_telegram = client.get_database(telegram_db_name)
telegram_channels = db_telegram.get_collection("channels")
telegram_dms = db_telegram.get_collection("dms")


@to_dict
class GroupConfig:
    def __init__(self, started=False, introduced=False, unleashed=False, count=None):
        self.started: bool = started
        self.introduced: bool = introduced
        self.unleashed: bool = unleashed
        self.count: int = count

    @abstractmethod
    def to_dict(self) -> Dict:
        pass

    def update_config(self, data: dict):
        return {**self.to_dict(), **data}


# ====== Nostr ======
@to_dict
class NostrEvent(Event):
    def __init__(self, event: Event):
        super().__init__(event)

    @abstractmethod
    def to_dict(self):
        pass


@to_dict
class MongoNostrEvent(NostrEvent, GroupConfig):
    def __init__(self, nostr_event: NostrEvent):
        self.nostr_event: NostrEvent = NostrEvent.__init__(nostr_event)
        self.messages = []
        self.history = []
        if self.nostr_event.kind() != 4:
            self.group_config = GroupConfig.__init__(started=True, introduced=True, unleashed=False, count=None)


# ====== Telegram Types ======
class TelegramMessage(Message):
    def __init__(self, message: Message):
        super().__init__(message)

    @abstractmethod
    def to_dict(self):
        pass


class MongoTelegramMessage(TelegramMessage, GroupConfig):
    def __init__(self, telegram_message: TelegramMessage):
        self.telegram_message: TelegramMessage = TelegramMessage.__init__(telegram_message)
        self.messages = []
        self.history = []
        telegram_chat: Chat = try_get(self.telegram_message, "chat")
        telegram_chat_type: str = try_get(telegram_chat, "type")
        if telegram_chat_type != "private":
            self.group_config = GroupConfig.__init__(started=True, introduced=True, unleashed=False, count=None)


@to_dict
class MongoNostr:
    def __init__(self):
        self.channels = nostr_channels
        self.dms = nostr_dms

    @try_except
    def known_channels(self) -> List[MongoNostrEvent]:
        return [MongoNostrEvent(channel) for channel in self.channels.find()]

    @try_except
    def known_channel_ids(self) -> List[EventId]:
        return [channel.id() for channel in self.known_channels()]

    @try_except
    def known_channel_invite_authors(self) -> List[PublicKey]:
        return [channel.pubkey() for channel in self.known_channels()]

    @try_except
    def known_dms(self) -> List[MongoNostrEvent]:
        return [MongoNostrEvent(dm) for dm in self.dms.find()]

    @try_except
    def known_dm_pubkeys(self) -> List[PublicKey]:
        return [MongoNostrEvent(dm).pubkey() for dm in self.dms.find()]


@to_dict
class MongoTelegram:
    def __init__():
        pass


@to_dict
class MongoAbbot(MongoNostr, MongoTelegram):
    def __init__(self, db_name):
        self.db_name = db_name
        self.channels: Collection[_DocumentType] | None = None
        self.dms: Collection[_DocumentType] | None = None
        if db_name == "telegram":
            self.channels = telegram_channels
            self.dms = telegram_dms
        elif db_name == "nostr":
            self.channels = nostr_channels
            self.dms = nostr_dms

    @abstractmethod
    def to_dict(self):
        pass

    # create docs
    @try_except
    def insert_one_channel(self, channel: Dict) -> InsertOneResult:
        return self.channels.insert_one(channel)

    @try_except
    def insert_many_channels(self, channels: List[Dict]) -> InsertManyResult:
        return self.channels.insert_many(channels)

    @try_except
    def insert_one_dm(self, direct_message: Dict) -> InsertOneResult:
        return self.dms.insert_one(direct_message)

    @try_except
    def insert_many_dms(self, direct_messages: List[Dict]) -> InsertManyResult:
        return self.dms.insert_many(direct_messages)

    # read documents
    @try_except
    def find_channels(self, filter: {}) -> List[MongoNostrEvent | MongoTelegramMessage]:
        return [MongoNostrEvent(channel) for channel in self.channels.find(filter)]

    @try_except
    def find_channels_cursor(self, filter: {}) -> Cursor:
        return self.channels.find(filter)

    @try_except
    def find_one_channel(self, filter: {}) -> MongoNostrEvent:
        return MongoNostrEvent(self.channels.find_one(filter))

    @try_except
    def find_one_dm(self, filter: {}) -> Optional[_DocumentType]:
        return self.dms.find_one(filter)

    @try_except
    def find_dms(self, filter: {}) -> List[MongoNostrEvent]:
        return [MongoNostrEvent(dm) for dm in self.dms.find(filter)]

    @try_except
    def find_dms_cursor(self, filter: {}) -> Cursor:
        return self.dms.find(filter)

    # update docs
    @try_except
    def update_one_channel(self, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        return self.channels.update_one(filter, {"$set": {**update}}, upsert)

    @try_except
    def update_one_dm(self, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        return self.dms.update_one(filter, {"$set": {**update}}, upsert)

    # custom reads
    @try_except
    def get_group_config(self, id: str) -> Optional[_DocumentType]:
        channel_doc = self.find_one_channel({"id": id})
        if channel_doc == None:
            return error("Channel does not exist")
        return channel_doc
