from abc import abstractmethod
from datetime import datetime
from cli_args import TELEGRAM_MODE, TEST_MODE, DEV_MODE
from typing import Dict, List, Optional, Tuple
from nostr_sdk import PublicKey, EventId, Event
from telegram import Chat, ChatMember, Message
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult
from bson.typings import _DocumentType
from constants import INTRODUCTION
from ..logger import bot_error, bot_debug
from ..utils import to_dict, error, try_get
from ..abbot.env import DATABASE_CONNECTION_STRING
from ..abbot.exceptions.exception import try_except
from ..abbot.config import BOT_CORE_SYSTEM_DM, BOT_CORE_SYSTEM_CHANNEL

client = MongoClient(host=DATABASE_CONNECTION_STRING)

if TEST_MODE:
    telegram_db_name = "test_telegram"
    nostr_db_name = "test_nostr"
elif DEV_MODE:
    telegram_db_name = "dev_telegram"
    nostr_db_name = "dev_nostr"
else:
    telegram_db_name = "telegram"
    nostr_db_name = "nostr"

bot_debug.log(__name__, f"telegram_db_name={telegram_db_name}")
db_nostr = client.get_database(nostr_db_name)
nostr_channels = db_nostr.get_collection("channel")
bot_channel_invites = db_nostr.get_collection("channel_invite")
nostr_dms = db_nostr.get_collection("dm")

db_telegram = client.get_database(telegram_db_name)
telegram_channels = db_telegram.get_collection("channel")
telegram_dms = db_telegram.get_collection("dm")

db_prices = client.get_database("prices")
btcusd = db_prices.get_collection("btcusd")


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
@to_dict
class TelegramDM:
    def __init__(self, message: Message):
        self.id: int = message.chat.id
        self.username: str = message.from_user.username
        self.created_at: datetime = datetime.now()
        self.messages = [message.to_dict()]
        self.history = [{"role": "system", "content": BOT_CORE_SYSTEM_DM}, {"role": "user", "content": message.text}]


@to_dict
class MongoAbbot(MongoNostr, MongoTelegram):
    def __init__(self, db_name):
        self.db_name = db_name
        if db_name == "telegram":
            self.channels: Collection[_DocumentType] = telegram_channels
            self.dms: Collection[_DocumentType] = telegram_dms
        elif db_name == "nostr":
            self.channels: Collection[_DocumentType] = nostr_channels
            self.dms: Collection[_DocumentType] = nostr_dms

    @abstractmethod
    def to_dict(self):
        pass


class TelegramGroup(GroupConfig):
    async def __init__(self, message: Message, admins: Tuple[ChatMember]):
        self.title: str = message.chat.title
        self.id: int = message.chat.id
        self.created_at: datetime = datetime.now()
        self.type: str = message.chat.type
        self.admins: List = admins
        self.balance: int = 50000
        self.messages = []
        self.history = []
        self.config = GroupConfig(started=True, introduced=True, unleashed=False, count=None)


@to_dict
class MongoNostr:
    def __init__(self):
        self.channels = nostr_channels
        self.dms = nostr_dms

    def known_channels(self) -> List[MongoNostrEvent]:
        return [MongoNostrEvent(channel) for channel in self.channels.find()]

    def known_channel_ids(self) -> List[EventId]:
        return [channel.id() for channel in self.known_channels()]

    def known_channel_invite_authors(self) -> List[PublicKey]:
        return [channel.pubkey() for channel in self.known_channels()]

    def known_dms(self) -> List[MongoNostrEvent]:
        return [MongoNostrEvent(dm) for dm in self.dms.find()]

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
        if db_name == "telegram":
            self.channels: Collection[_DocumentType] = telegram_channels
            self.dms: Collection[_DocumentType] = telegram_dms
        elif db_name == "nostr":
            self.channels: Collection[_DocumentType] = nostr_channels
            self.dms: Collection[_DocumentType] = nostr_dms

    @abstractmethod
    def to_dict(self):
        pass

    def insert_one_price(self, price: Dict) -> InsertOneResult:
        return btcusd.insert_one(price)

    # create docs
    def insert_one_channel(self, channel: Dict) -> InsertOneResult:
        return self.channels.insert_one(channel)

    def insert_many_channels(self, channels: List[Dict]) -> InsertManyResult:
        return self.channels.insert_many(channels)

    def insert_one_dm(self, direct_message: Dict) -> InsertOneResult:
        return self.dms.insert_one(direct_message)

    def insert_many_dms(self, direct_messages: List[Dict]) -> InsertManyResult:
        return self.dms.insert_many(direct_messages)

    # read documents
    def find_channels(self, filter: {}) -> List[Optional[_DocumentType]]:
        return [channel for channel in self.channels.find(filter)]

    def find_channels_cursor(self, filter: {}) -> Cursor:
        return self.channels.find(filter)

    def find_one_channel(self, filter: {}) -> Optional[_DocumentType]:
        return self.channels.find_one(filter)

    def find_one_channel_and_update(self, filter: {}, update: Dict) -> Optional[_DocumentType]:
        return self.channels.find_one_and_update(filter, update, return_document=True)

    def find_one_dm(self, filter: {}) -> Optional[_DocumentType]:
        return self.dms.find_one(filter)

    def find_one_dm_and_update(self, filter: {}, update: Dict) -> Optional[_DocumentType]:
        return self.dms.find_one_and_update(filter, update, return_document=True)

    def find_dms(self, filter: {}) -> List[Optional[_DocumentType]]:
        return [dm for dm in self.dms.find(filter)]

    def find_dms_cursor(self, filter: {}) -> Cursor:
        return self.dms.find(filter)

    # update docs
    def update_one(self, collection: str, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        if collection == "dm":
            return self.update_one_dm(filter, update, upsert)
        else:
            return self.update_one_channel(filter, update, upsert)

    def update_one_history(self, collection: str, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        if collection == "dm":
            return self.dms.update_one(filter, {"$push": {"history": update}}, upsert)
        else:
            return self.channels.update_one(filter, {"$push": {"history": update}}, upsert)

    def update_one_channel(self, filter: {}, update: Dict, upsert: bool = True) -> UpdateResult:
        return self.channels.update_one(filter, {"$set": {**update}}, upsert)

    def update_one_dm(self, filter, update: Dict, upsert: bool = True) -> UpdateResult:
        return self.dms.update_one(filter, update, upsert)

    # custom reads
    def get_group_config(self, id: str) -> Optional[_DocumentType]:
        channel_doc = self.find_one_channel({"id": id})
        if channel_doc == None:
            return error("Channel does not exist")
        return channel_doc

    def get_group_balance(self, id) -> int:
        group: TelegramGroup = self.find_one_channel({"id": id})
        return try_get(group, "balance")

    def get_group_history(self, id) -> int:
        group: TelegramGroup = self.find_one_channel({"id": id})
        return try_get(group, "history", default=[])


db_name = "telegram" if TELEGRAM_MODE else "nostr"
mongo_abbot = MongoAbbot(db_name)
