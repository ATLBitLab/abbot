import uuid

from typing import Dict, List, Optional, Tuple, Callable, Tuple

from nostr_sdk import Keys, Client, Filter, Event, EventBuilder, nip04_decrypt

from src.lib.abbot.core import Abbot
from lib.logger import bot_debug, bot_error
from lib.abbot.exceptions.exception import try_except
from lib.db.mongo import NostrEvent, MongoNostr, InsertOneResult, UpdateResult
from lib.db.utils import successful_insert_one, successful_update_many

mongo_nostr: MongoNostr = MongoNostr()

DM: int = 4
CHANNEL_CREATE: int = 40
CHANNEL_META: int = 41
CHANNEL_MESSAGE: int = 42
CHANNEL_HIDE: int = 43
CHANNEL_MUTE: int = 44
BOT_CHANNEL_INVITE: int = 21021

RELAYS: List[str] = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
    "wss://nostr.atlbitlab.com",
]

INTRODUCTION = """
Hey! The name's Abbot but you can think of me as your go-to guide for all things Bitcoin.
AKA the virtual Bitcoin whisperer. 😉
Here's the lowdown on how to get my attention:
1. Slap an @ before your message in the group chat - I'll come running to answer.
2. Feel more comfortable replying directly to my messages? Go ahead! I'm all ears.. err.. code.
3. Fancy a one-on-one chat? Slide into my DMs.
Now, enough with the rules! Let's dive into the world of Bitcoin together!
Ready. Set. Stack Sats! 🚀
"""


class NostrBotBuilder:
    def __init__(self, custom_filters: Optional[List[Filter]] = [], author_whitelist: Optional[List[str]] = []):
        from lib.abbot.env import BOT_NOSTR_SK as sk

        self.keys = Keys.from_sk_str(sk)
        self._secret_key = self.keys.secret_key()
        self.public_key = self.keys.public_key()
        self.client = Client(Keys(self._secret_key))
        self.author_whitelist: Optional[List[str]] = author_whitelist
        self.custom_filters = custom_filters
        self.default_filters_list: List[Filter] = [
            Filter().kind(4).pubkey(self.public_key),
            Filter().kind([40, 41]).authors(author_whitelist),
            Filter().kind(42).pubkey(self.public_key),
            Filter().kind(21021).pubkey(self.public_key).authors(self.author_whitelist),
        ]
        self.event_handlers: Dict[int, Callable] = {}

    @try_except
    def add_handler(self, group: int, handler: Callable):
        if group not in self.event_handlers:
            self.event_handlers[group] = handler
        self.event_handlers = dict(sorted(self.event_handlers.items()))
        return self

    @try_except
    def add_handlers(self, handlers: List[Tuple[int, Callable]]):
        for group, handler_fn in handlers:
            self.add_handler(group, handler_fn)
        return self

    @try_except
    def add_relays_connect_and_start_client(self):
        bot_debug.log("add_relays_and_connect")
        for relay in RELAYS:
            bot_debug.log(f"Adding relay {relay}")
            self.client.add_relay(relay)
            self.client.connect()
        sub_id = uuid.uuid4().hex
        bot_debug.log(f"Subscriptions added with id {sub_id}")
        self.client.start()

    @try_except
    def send_direct_message(self, answer: str, incoming_dm: Event):
        event_builder: EventBuilder = EventBuilder(4, answer, incoming_dm.tags())
        event: Event = event_builder.to_event(self.keys)
        return self.client.send_event(event)

    @try_except
    def decrypt_direct_message(self, encrypted_dm: Event):
        return nip04_decrypt(self._secret_key, encrypted_dm.pubkey(), encrypted_dm.content())

    @try_except
    def send_greeting_to_channel(self, channel_id: str):
        event_builder: EventBuilder = EventBuilder(
            kind=CHANNEL_MESSAGE, content=INTRODUCTION, tags=[["e", channel_id, RELAYS[0], "root"]]
        )
        event: Event = event_builder.to_event(self.keys)
        return self.client.send_event(event)

    @try_except
    def run(self):
        while True:
            for event in self.client.get_events_of(self.default_filters_list, None):
                event: Event = event
                if event.verify():
                    event_json: dict = event.as_json()
                    print("event", event.as_json())
                    kind: int = event.kind()
                    nostr_event: NostrEvent = NostrEvent(**event_json)
                    nostr_event_dict: Dict = nostr_event.to_dict()
                    if kind == 4:
                        result: InsertOneResult = mongo_nostr.insert_one_dm(nostr_event_dict)
                        if not successful_insert_one(result):
                            bot_error.log(f"insert_dm failed: {nostr_event_dict}")
                            break
                        self.handle_dm(nostr_event)
                    elif kind == 40:
                        result: InsertOneResult = mongo_nostr.insert_one_channel(nostr_event_dict)
                        if not successful_insert_one(result):
                            bot_error.log(f"insert_one_channel failed: {nostr_event_dict}")
                            break
                        self.handle_channel_create(nostr_event)
                    elif kind in [41, 42, 43, 44]:
                        result: UpdateResult = mongo_nostr.update_one_channel(
                            {"id": nostr_event.id}, {"$push": {"messages": nostr_event_dict}}
                        )
                        if not successful_update_many(result):
                            bot_error.log(f"update_one_channel failed: {nostr_event_dict}")
                            break
                        self.handle_channel_event(kind, nostr_event_dict)

    @try_except
    def handle_dm(self, incoming_dm: NostrEvent):
        content = self.decrypt_direct_message(incoming_dm)
        abbot = Abbot(f"{incoming_dm.pubkey}-{self.public_key}")
        abbot.update_history({"role": "user", "content": content})
        answer: str = abbot.chat_completion()
        event_id: str = self.send_direct_message(answer, incoming_dm)
        bot_debug.log(f"handle_dm: {event_id}")

    @try_except
    def handle_channel_event(self):
        print("handler")

    @try_except
    def handle_channel_create(self):
        print("handler")

    @try_except
    def handle_channel_meta(self):
        print("handler")

    @try_except
    def handle_channel_message(self):
        print("handler")

    @try_except
    def handle_channel_hide(self):
        print("handler")

    @try_except
    def handle_channel_mute(self):
        print("handler")

    @try_except
    def handle_channel_invite(self):
        print("handler")
