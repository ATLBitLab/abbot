import json
import time
import uuid
import asyncio
import IPython
from traceback import format_exc, format_tb
from typing import Dict, List, Optional, Set, Tuple, Callable, Tuple

from nostr_sdk import Keys, Client, Filter, Event, EventId, EventBuilder, PublicKey, SecretKey, nip04_decrypt

from lib.logger import bot_debug, bot_error

from lib.db.utils import successful_insert_one
from lib.db.mongo import MongoNostrEvent, NostrEvent, MongoNostr, InsertOneResult

from lib.abbot.core import Abbot
from lib.abbot.config import ORG_HEX_PUBKEY
from lib.abbot.exceptions.exception import AbbotException, try_except

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
FILTER = Filter()


class NostrBotBuilder:
    def __init__(
        self,
        custom_filters: Optional[List[Filter]] = [],
    ):
        self.io_loop = asyncio.get_event_loop()
        from lib.abbot.env import BOT_NOSTR_SK as sk

        self.keys = Keys.from_sk_str(sk)
        self._secret_key: SecretKey = self.keys.secret_key()
        self.public_key = self.keys.public_key()
        self.public_key_hex = self.public_key.to_hex()
        self.client: Client = Client(Keys(self._secret_key))

        self.known_channels: List[MongoNostrEvent] = mongo_nostr.known_channels()
        self.known_channel_ids: List[EventId] = mongo_nostr.known_channel_ids()

        self.known_dms: List[MongoNostrEvent] = mongo_nostr.known_dms()
        self.known_dm_public_keys: List[PublicKey] = mongo_nostr.known_dm_pubkeys()

        self.author_whitelist: List[PublicKey] = mongo_nostr.known_channel_invite_authors()
        self.all_dms_with_abbot: Set[Event] = set()
        self.filters_list = [
            # filter for new DMs to Abbot
            ("all_dms", FILTER.kind(DM).pubkey(self.public_key)),
            # filter for updates to all known DMs to Abbot
            ("known_dms", FILTER.kind(DM).authors(self.known_dm_public_keys)),
            # filter for channel updates (meta, hide, mute, messages) from known channels
            (
                "known_channel_updates",
                FILTER.kinds([CHANNEL_META, CHANNEL_MESSAGE, CHANNEL_HIDE, CHANNEL_MUTE]).events(
                    self.known_channel_ids
                ),
            )
            # filter for new channel invites from ATL BitLab implying someone paid via abbot.atlbitlab.com
            (
                "new_channel_invites",
                FILTER.kind(BOT_CHANNEL_INVITE).pubkey(self.public_key).author(ORG_HEX_PUBKEY),
            ),
        ]
        self.event_handlers: Dict[int, Callable] = {}
        if custom_filters:
            self.filters_list = [*self.filters_list, custom_filters]
        for filter_name, filter in self.filters_list:
            if filter_name == "all_dms":
                self.all_dms_with_abbot.add(filter)
        self.new_dms_with_abbot: Set[Event] = set(self.known_dms, self.all_dms_with_abbot)

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
        fn = __name__
        bot_debug.log(fn, "add_relays_and_connect")
        for relay in RELAYS:
            bot_debug.log(fn, f"Adding relay {relay}")
            self.client.add_relay(relay)
            self.client.connect()
        sub_id = uuid.uuid4().hex
        bot_debug.log(fn, f"Subscriptions added with id {sub_id}")
        self.client.start()

    @try_except
    def send_direct_message(self, answer: str, incoming_dm: NostrEvent):
        event_builder: EventBuilder = EventBuilder(4, answer, incoming_dm.tags)
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
        fn = f"{__name__}:"
        try:
            for event in self.client.get_events_of(self.filters_list, None):
                event: Event = event
                if event.verify():
                    event_json: dict = json.loads(event.as_json())
                    kind: int = event.kind()
                    db_nostr_event: MongoNostrEvent = MongoNostrEvent(event_json)
                    bot_debug.log(fn, f"db_nostr_event {db_nostr_event}")
                    if kind == 4:
                        result: InsertOneResult = mongo_nostr.insert_one_dm(db_nostr_event.to_dict())
                        bot_debug.log(fn, f"dm={dm}")
                        if not successful_insert_one(result):
                            bot_error.log(fn, f"inset_one_dm Failed")
                            result: InsertOneResult = mongo_nostr.insert_one_dm(db_nostr_event)
                            bot_debug.log(fn, f"result {result}")
                            dm: Dict = mongo_nostr.find_one_dm({"id": sender_pubkey})
                            if not successful_insert_one(result):
                                bot_error.log(f"insert_dm failed: {nostr_event_dict}")
                                time.sleep(1)
                        IPython.embed()
                        self.handle_dm(event)
                    # elif kind == 40:
                    #     result: InsertOneResult = mongo_nostr.insert_one_channel(nostr_event_dict)
                    #     if not successful_insert_one(result):
                    #         bot_error.log(f"insert_one_channel failed: {nostr_event_dict}")
                    #         time.sleep(1)
                    #     self.handle_channel_create(nostr_event)
                    # elif kind in [41, 42, 43, 44]:
                    #     result: UpdateResult = mongo_nostr.update_one_channel(
                    #         {"id": nostr_event.id}, {"$push": {"messages": nostr_event_dict}}
                    #     )
                    #     if not successful_update_many(result):
                    #         bot_error.log(f"update_one_channel failed: {nostr_event_dict}")
                    #         time.sleep(1)
                    #     self.handle_channel_event(kind, nostr_event_dict)
        except AbbotException as abbot_exception:
            abbot_exception = AbbotException(
                abbot_exception, format_exc(), format_tb(abbot_exception.__traceback__)[:-1]
            )
            bot_error.log(f"Main Loop Error: {abbot_exception}")
            time.sleep(5)

    @try_except
    def handle_dm(self, dm_event: Event):
        fn = __name__
        bot_debug.log(fn, f"dm_event={dm_event}")
        bot_debug.log(fn, f"type(dm_event)={type(dm_event)}")
        content: str = self.decrypt_direct_message(dm_event)
        sender: str = dm_event.pubkey().to_hex()
        bot_debug.log(fn, f"content={content}")
        bot_debug.log(fn, f"sender={sender}")
        bot_debug.log(fn, f"self.public_key={self.public_key}")
        IPython.embed()
        abbot = Abbot(sender, "dm")
        bot_debug.log(fn, f"abbot: {abbot}")
        abbot.update_history({"role": "user", "content": content})
        answer: str = abbot.chat_completion()
        bot_debug.log(fn, f"content={content}")

        event_id: str = self.send_direct_message(answer, dm_event)
        bot_debug.log(fn, f"handle_dm: {event_id}")

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
