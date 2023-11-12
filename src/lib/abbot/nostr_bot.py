import uuid
import json
import asyncio
import websockets
from attr import dataclass
from typing import Dict, List, Optional, Tuple, Callable, Coroutine, Tuple

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer
from tornado.iostream import IOStream, StreamClosedError

from nostr_sdk import Keys, Client, EventBuilder, Filter

from pynostr.event import Event
from pynostr.event import EventKind
from pynostr.key import PrivateKey, PublicKey
from pynostr.relay_manager import RelayManager, RelayPolicy
from pynostr.filters import FiltersList, Filters
from pynostr.encrypted_dm import EncryptedDirectMessage

from lib.utils import try_get
from lib.abbot.env import BOT_NOSTR_PK
from lib.logger import bot_debug, bot_error
from lib.abbot.exceptions.exception import try_except

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


class AbbotNostr:
    relay_manager: RelayManager = RelayManager()
    io_loop: IOLoop = relay_manager.io_loop
    notices: List = []
    events: List = []

    def __init__(self, custom_filters: Filters = None, author_whitelist: Optional[List[str]] = []):
        import lib.abbot.env as e

        self._private_key = Keys.from_sk_str(e.BOT_NOSTR_SK)
        self.public_key = self._private_key.public_key()
        self.client = Client(Keys(self._private_key))
        self.author_whitelist: Optional[List[str]] = author_whitelist
        self.custom_filters = custom_filters
        self.default_filters_list: List[Filter] = [
            Filter().kind(4).pubkey(self.public_key),
            Filter().kinds([40, 42]).pubkey(self.public_key),
            Filter().kind(21021).pubkey(self.public_key).authors(self.author_whitelist),
        ]

    def _instantiate_direct_message(
        self,
        partner_pk: str,
        cleartext: str | None,
        encrypted: str | None,
        reference_event_id: str | None = None,
    ) -> EncryptedDirectMessage:
        assert partner_pk != None, "Error: partner_pk required!"
        assert None not in (cleartext, encrypted), "Error: cleartext or encrypted required"
        return EncryptedDirectMessage(self.public_key.to_hex(), partner_pk, cleartext, encrypted, reference_event_id)

    @gen.coroutine
    @try_except
    def add_relays_and_connect(self):
        bot_debug.log("add_relays_and_connect")
        for relay in RELAYS:
            bot_debug.log(f"Adding relay {relay}")
            self.client.add_relay(relay)
            self.client.connect()
        sub_id = uuid.uuid4().hex
        bot_debug.log(f"Subscriptions added with id {sub_id}")
        self.client.start()

    @gen.coroutine
    @try_except
    def start_client(self):
        bot_debug.log("Running relay sync ...")
        while True:
            for event in self.client.get_events_of(self.default_filters_list, None):
                print("event", event.as_json())

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
class NostrHandler:
    group: int
    handler_fn: Callable[[IOStream, Tuple], Coroutine[None, None, None]]

    def items(self):
        return self.__dict__.items()


class NostrBuilder:
    def __init__(
        self,
        host="127.0.0.1",
        port=8080,
    ):
        self.host = host
        self.port = port
        self.handlers: Dict[List[NostrHandler[int, Callable[[IOStream, Tuple], Coroutine[None, None, None]]]]] = {}

    @try_except
    def add_handler(self, group: int, handler: NostrHandler):
        if group not in self.handlers:
            self.handlers[group] = []
        self.handlers[group].append(handler)
        self.handlers = dict(sorted(self.handlers.items()))
        return self

    @try_except
    def add_handlers(self, handlers: List[NostrHandler]):
        for handler in handlers:
            self.add_handler(handler.group, handler.handler_fn)
        return self

    def handle_event(self, stream: IOStream, address: Tuple):
        print("handle_event")
        print("stream", stream)
        print("address", address)
        while True:
            try:
                print("while True try")
                data = yield stream.read_until()
                print("data", data)
                if not data:
                    bot_error.log(f"No client data")
                    yield stream.write(b"No client data\n")
                    break

                try:
                    data = json.loads(data)
                    print("jsonloads data", data)
                except:
                    pass
                event: Event = Event(data)  # Make sure Event is properly parsed from data
                print("event", event)
                kind: int = try_get(event, "kind")  # Assuming this function extracts the 'kind' from the event
                print("kind", kind)

                for group, handler in self.handlers.items():
                    print("group, handler", group, handler)
                    if group == kind:
                        yield handler(event, stream, address)
                        break
                bot_error.log(f"No matching handler for kind: {kind}")
                yield stream.write(b"No matching handler found\n")
                break

            except StreamClosedError:
                bot_error.log(f"StreamClosedError: Client {address} disconnected")
                break

    async def listen_to_websocket(self, url):
        async with websockets.connect(url) as websocket:
            while True:
                data = await websocket.recv()
                await self.handle_event(data)

    async def run(self):
        await asyncio.gather(*(self.listen_to_websocket(relay) for relay in RELAYS))


async def handle_dm(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_create(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_create(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_meta(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_message(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_hide(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_mute(stream: IOStream, address: Tuple):
    print("handler")


async def handle_channel_invite(stream: IOStream, address: Tuple):
    print("handler")
