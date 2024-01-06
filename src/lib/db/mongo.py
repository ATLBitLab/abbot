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

from ..logger import debug_bot
from ..utils import success, to_dict, try_get
from ..abbot.env import DATABASE_CONNECTION_STRING
from ..abbot.config import BOT_SYSTEM_OBJECT_GROUPS, BOT_SYSTEM_OBJECT_DMS

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

debug_bot.log(__name__, f"telegram_db_name={telegram_db_name}")

nostr_db = client.get_database(nostr_db_name)
nostr_channels = nostr_db.get_collection("channel")
nostr_dms = nostr_db.get_collection("dm")
nostr_channel_invites = nostr_db.get_collection("channel_invite")

telegram_db = client.get_database(telegram_db_name)
telegram_groups = telegram_db.get_collection("group")
telegram_dms = telegram_db.get_collection("dm")

bitcoin_prices = client.get_database("bitcoin_prices")
btcusd = bitcoin_prices.get_collection("btcusd")

db_prices = client.get_database("prices")
btcusd = db_prices.get_collection("btcusd")


@to_dict
class GroupConfig:
    def __init__(self, introduced=False, started=False, unleashed=False, count=None):
        self.introduced: bool = introduced
        self.started: bool = started
        self.unleashed: bool = unleashed
        self.count: int = count

    @abstractmethod
    def to_dict(self) -> Dict:
        pass

    def update_config(self, data: dict):
        return success("", data={**self.to_dict(), **data})


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
            self.groups_config = GroupConfig.__init__(started=True, introduced=True, unleashed=False, count=None)


# ====== Telegram Types ======
@to_dict
class TelegramDM:
    def __init__(self, message: Message):
        self.created_at: datetime = datetime.now()
        self.id: int = message.chat.id
        self.username: str = message.from_user.username
        self.type: str = message.chat.type
        self.messages = [message.to_dict()]
        self.history = [BOT_SYSTEM_OBJECT_DMS]

    @abstractmethod
    def to_dict(self):
        pass


class TelegramGroup(GroupConfig):
    def __init__(self, message: Message, admins: Tuple[ChatMember]):
        self.created_at: datetime = datetime.now()
        self.id: int = message.chat.id
        self.title: str = message.chat.title
        self.type: str = message.chat.type
        self.admins: List = admins
        self.balance: int = 5000
        self.messages = [message.to_dict()]
        self.history = [BOT_SYSTEM_OBJECT_GROUPS]
        self.config = GroupConfig(introduced=False, started=False, unleashed=False, count=None)


@to_dict
class MongoNostr:
    def __init__(self):
        self.groups = nostr_channels
        self.direct_messages = nostr_dms

    def known_channels(self) -> List[MongoNostrEvent]:
        return success("", data=[MongoNostrEvent(channel) for channel in self.groups.find()])

    def known_channel_ids(self) -> List[EventId]:
        return success("", data=[channel.id() for channel in self.known_channels()])

    def known_channel_invite_authors(self) -> List[PublicKey]:
        return success("", data=[channel.pubkey() for channel in self.known_channels()])

    def known_dms(self) -> List[MongoNostrEvent]:
        return success("", data=[MongoNostrEvent(dm) for dm in self.direct_messages.find()])

    def known_dm_pubkeys(self) -> List[PublicKey]:
        return success("", data=[MongoNostrEvent(dm).pubkey() for dm in self.direct_messages.find()])


@to_dict
class MongoTelegram:
    def __init__():
        pass


@to_dict
class MongoAbbot(MongoNostr, MongoTelegram):
    def __init__(self, db_name):
        self.db_name = db_name
        if db_name == "telegram":
            self.groups: Collection[_DocumentType] = telegram_groups
            self.direct_messages: Collection[_DocumentType] = telegram_dms
        elif db_name == "nostr":
            self.groups: Collection[_DocumentType] = nostr_channels
            self.direct_messages: Collection[_DocumentType] = nostr_dms

    @abstractmethod
    def to_dict(self):
        pass

    def insert_one_price(self, price: Dict) -> InsertOneResult:
        return btcusd.insert_one(price)

    def find_prices_cursor(self) -> InsertOneResult:
        return btcusd.find()

    def find_prices(self) -> List:
        return [price for price in btcusd.find()]

    # create docs
    def insert_one_group(self, channel: Dict) -> InsertOneResult:
        return self.groups.insert_one(channel)

    def insert_many_groups(self, groups: List[Dict]) -> InsertManyResult:
        return self.groups.insert_many(groups)

    def insert_one_dm(self, direct_message: Dict) -> InsertOneResult:
        return self.direct_messages.insert_one(direct_message)

    def insert_many_dms(self, direct_messages: List[Dict]) -> InsertManyResult:
        return self.direct_messages.insert_many(direct_messages)

    # read
    def find_groups(self, filter: Dict) -> List[Optional[_DocumentType]]:
        return [channel for channel in self.groups.find(filter, {"_id": 0})]

    def find_groups_cursor(self, filter: Dict) -> Cursor:
        return self.groups.find(filter, {"_id": 0})

    def find_one_group(self, filter: Dict) -> Optional[_DocumentType]:
        return self.groups.find_one(filter, {"_id": 0})

    def find_one_group_and_update(self, filter: Dict, update: Dict) -> Optional[_DocumentType]:
        return self.groups.find_one_and_update(
            filter,
            update,
            return_document=True,
            upsert=True,
            projection={"_id": 0},
        )

    def find_one_dm(self, filter: Dict) -> Optional[_DocumentType]:
        return self.direct_messages.find_one(filter, {"_id": 0})

    def find_one_dm_and_update(self, filter: Dict, update: Dict) -> Optional[_DocumentType]:
        return self.direct_messages.find_one_and_update(
            filter,
            update,
            return_document=True,
            upsert=True,
            projection={"_id": 0},
        )

    def find_dms(self, filter: Dict) -> List[Optional[_DocumentType]]:
        return [dm for dm in self.direct_messages.find(filter, {"_id": 0})]

    def find_dms_cursor(self, filter: Dict) -> Cursor:
        return self.direct_messages.find(filter, {"_id": 0})

    # update docs
    def update_one(self, collection: str, filter: Dict, update: Dict) -> UpdateResult:
        if collection == "dm":
            return self.update_one_dm(filter, update, return_document=True, upsert=True)
        else:
            return self.update_one_group(filter, update, return_document=True, upsert=True)

    def update_one_group(self, filter: Dict, update: Dict) -> UpdateResult:
        return self.groups.update_one(filter, update, return_document=True, upsert=True)

    def update_one_dm(self, filter, update: Dict) -> UpdateResult:
        return self.direct_messages.update_one(filter, update, return_document=True, upsert=True)

    # custom reads
    def get_group_config(self, filter: {}) -> Optional[_DocumentType]:
        group: TelegramGroup = self.find_one_group(filter)
        return try_get(group, "config")

    def get_group_balance(self, filter: {}) -> int:
        group: TelegramGroup = self.find_one_group(filter)
        return try_get(group, "balance")

    def get_group_history(self, filter: {}) -> int:
        group: TelegramGroup = self.find_one_group(filter)
        return try_get(group, "history", default=[])

    def get_dm_history(self, filter) -> int:
        dm: TelegramDM = self.find_one_dm(filter)
        return try_get(dm, "history", default=[])

    def group_does_exist(self, filter) -> int:
        group: TelegramGroup = self.find_one_group(filter)
        return group != None

    def dm_does_exist(self, filter) -> int:
        dm: TelegramDM = self.find_one_dm(filter)
        return dm != None


db_name = "telegram" if TELEGRAM_MODE else "nostr"
mongo_abbot = MongoAbbot(db_name)
