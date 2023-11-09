import uuid
import asyncio
from asyncio import StreamReader, StreamWriter
from attr import dataclass

from pynostr.key import PrivateKey, PublicKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.event import Event
from typing import Any, List, Optional, Dict, Tuple, Union
import types as _types

from lib.utils import try_get
from lib.abbot.env import BOT_NOSTR_PK, BOT_NOSTR_NPUB, BOT_NOSTR_SK
from lib.abbot.config import BOT_CORE_SYSTEM
from lib.logger import debug_logger
from lib.abbot.exceptions.exception import try_except
from lib.abbot.core import Abbot

DM: EventKind = EventKind.ENCRYPTED_DIRECT_MESSAGE  # 4
CHANNEL_CREATE: EventKind = EventKind.CHANNEL_CREATE  # 40
CHANNEL_META: EventKind = EventKind.CHANNEL_META  # 41
CHANNEL_MESSAGE: EventKind = EventKind.CHANNEL_MESSAGE  # 42
CHANNEL_HIDE: EventKind = EventKind.CHANNEL_HIDE  # 43
CHANNEL_MUTE: EventKind = EventKind.CHANNEL_MUTE  # 44
BOT_CHANNEL_INVITE: EventKind = EventKind.BOT_CHANNEL_INVITE  # 21021

RELAYS: List[str] = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol/",
    "wss://relay.primal.net",
    "wss://relay.snort.social/",
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


@try_except
class AbbotNostr(Abbot):
    relay_manager = RelayManager(timeout=6)
    notices = []
    events = []

    def __init__(self, custom_filters: Filters = None, author_whitelist: Optional[List[str]] = None):
        from env import BOT_NOSTR_SK

        self._private_key = PrivateKey.from_hex(BOT_NOSTR_SK)
        self.public_key: PublicKey = self._private_key.public_key
        self.author_whitelist: Optional[List[str]] = author_whitelist
        self.custom_filters = custom_filters
        self.default_filters_list: FiltersList = FiltersList(
            [
                Filters(kinds=[DM], pubkey_refs=[BOT_NOSTR_PK], limit=1000),
                Filters(kinds=[CHANNEL_CREATE, CHANNEL_MESSAGE], pubkey_refs=[BOT_NOSTR_PK], limit=1000),
                Filters(
                    kinds=[BOT_CHANNEL_INVITE], pubkey_refs=[BOT_NOSTR_PK], authors=self.author_whitelist, limit=1000
                ),
            ]
        )

    def _instantiate_direct_message(
        self,
        partner_pk: str,
        cleartext: str | None,
        encrypted: str | None,
        reference_event_id: str | None = None,
    ) -> EncryptedDirectMessage:
        assert partner_pk != None, "Error: partner_pk required!"
        assert None not in (cleartext, encrypted), "Error: cleartext or encrypted required"
        return EncryptedDirectMessage(self.public_key.hex(), partner_pk, cleartext, encrypted, reference_event_id)

    @try_except
    def add_relays_and_subscribe(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)
        self.relay_manager.add_subscription_on_all_relays(uuid.uuid4().hex, self.default_filters_list)

    @try_except
    def run_relay_sync(self):
        self.relay_manager.run_sync()

    @try_except
    def get_message_pool(self):
        return self.relay_manager.message_pool

    @try_except
    def poll_for_notices(self):
        while self.relay_manager.message_pool.has_notices():
            notice = self.relay_manager.message_pool.get_notice()
            self.notices.append(notice)

    @try_except
    def poll_for_events(self):
        while self.relay_manager.message_pool.has_events():
            event = self.relay_manager.message_pool.get_event().event
            if event.verify():
                self.events.append(event)
                yield event

    @try_except
    def get_notices(self):
        return self.notices

    @try_except
    def get_events(self):
        return self.events

    @try_except
    def get_message_pool_notices(self):
        return self.relay_manager.message_pool.notices

    @try_except
    def get_message_pool_events(self):
        return self.relay_manager.message_pool.events

    @try_except
    def unsubscribe(self, url, id: str):
        self.relay_manager.close_subscription_on_relay(url, id)

    @try_except
    def disconnect_from_relays(self):
        self.relay_manager.close_connections()

    @try_except
    async def handle_dm(self, event: Event, reader: StreamReader, writer: StreamWriter):
        tag_dict = event.get_tag_dict()
        if event.has_pubkey_ref():
            p = try_get(tag_dict, "p")
        direct_message = self.decrypt_direct_message(p, event.content, event.id)

    @try_except
    def encrypt_direct_message(self, partner_pk: str, cleartext_content: str):
        encrypted_direct_message: EncryptedDirectMessage = self._instantiate_direct_message(
            partner_pk, cleartext_content=cleartext_content
        )
        encrypted_direct_message.encrypt(self._private_key.hex())
        encrypted_direct_message_event = encrypted_direct_message.to_event()
        encrypted_direct_message_event.sign(self.public_key.hex())
        return encrypted_direct_message_event

    @try_except
    def decrypt_direct_message(
        self,
        partner_pk: str,
        encrypted_message: str,
        ref_event_id: str | None = None,
    ):
        encrypted_direct_message: EncryptedDirectMessage = self._instantiate_direct_message(
            partner_pk, encrypted_message=encrypted_message, reference_event_id=ref_event_id
        )
        encrypted_direct_message.decrypt(self._private_key.hex())
        return encrypted_direct_message

    @try_except
    def send_greeting_to_channel(self, channel_id: str):
        event = Event(
            kind=CHANNEL_MESSAGE,
            pubkey=self.public_key.hex(),
            content=INTRODUCTION,
            tags=[["e", channel_id, RELAYS[0], "root"]],
        )
        event.sign(self._private_key.hex())
        print(event)
        self.publish_event(event)

    @try_except
    def publish_event(self, event):
        self.relay_manager.publish_event(event)
        self.relay_manager.run_sync()


@dataclass
@try_except
class NostrEventHandler:
    group: int
    kind: int
    handler: _types.FunctionType
    if group == 0:
        assert kind == 4
    elif group == 1:
        assert kind in [40, 41, 42, 43, 44, 21021]


class NostrBotBuilder(AbbotNostr):
    def __init__(
        self,
        event: Event,
        reader: StreamReader,
        writer: StreamWriter,
        host="127.0.0.1",
        port=8888,
    ):
        self.event = event
        self.reader = reader
        self.writer = writer
        self.host = host
        self.port = port
        self.handlers: Dict[int, List[NostrEventHandler]] = {}

    def get_handlers(self) -> object:
        return self

    @try_except
    async def handle_dm(self):
        pass

    @try_except
    async def handle_channel_create(self):
        pass

    @try_except
    async def handle_channel_create(self):
        pass

    @try_except
    async def handle_channel_meta(self):
        pass

    @try_except
    async def handle_channel_message(self):
        pass

    @try_except
    async def handle_channel_hide(self):
        pass

    @try_except
    async def handle_channel_mute(self):
        pass

    @try_except
    async def handle_channel_invite(self):
        pass

    @try_except
    def add_handler(self, handler: NostrEventHandler, group: int):
        if group not in self.handlers:
            self.handlers[group] = []
            self.handlers = dict(sorted(self.handlers.items()))
        self.handlers[group] = handler
        return self

    """
    {
       -1: [NostrEventHandler(...)],
        1: [CallbackQueryHandler(...), CommandHandler(...)]
    }
    """

    @try_except
    def add_handlers(self, handlers: List[Dict[int, NostrEventHandler]], group: int):
        for handler in handlers:
            self.add_handler(handler, group)
        return self

    @try_except
    async def handle_event(self, reader: StreamReader, writer: StreamWriter):
        while True:
            data = await reader.read(100)
            if not data:
                break
            # TODO: Replace the following line with your actual message parsing logic
            event: Event = data
            kind: int = try_get(event, "kind")
            id: str = try_get(event, "id")
            abbot_nostr = AbbotNostr(Abbot(f"AbbotNostr-{id}", BOT_NOSTR_NPUB, BOT_CORE_SYSTEM, id))
            for handler in self.handlers:
                if try_get(handler, kind) == kind:
                    await abbot_nostr[handler(data, reader, writer)]

    @try_except
    async def run(self):
        server = await asyncio.start_server(self.handle_event, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"Serving on {addr}")
        async with server:
            await server.serve_forever()


nostr_bot: NostrBotBuilder = NostrBotBuilder()
handlers: NostrBotBuilder = nostr_bot.get_handlers()
nostr_bot.add_handlers(
    [
        NostrEventHandler(4, handlers.handle_dm),
        NostrEventHandler(40, handlers.handle_channel_create),
        NostrEventHandler(41, handlers.handle_channel_meta),
        NostrEventHandler(42, handlers.handle_channel_message),
        NostrEventHandler(43, handlers.handle_channel_hide),
        NostrEventHandler(44, handlers.handle_channel_mute),
        NostrEventHandler(21021, handlers.handle_channel_invite),
    ]
)
