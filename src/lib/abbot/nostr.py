import os
import uuid
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.event import Event
from typing import List, Optional

from lib.abbot.exceptions.exception import try_except
from lib.utils import try_get

DM = EventKind.ENCRYPTED_DIRECT_MESSAGE  # 4
CHANNEL_CREATE = EventKind.CHANNEL_CREATE  # 40
CHANNEL_META = EventKind.CHANNEL_META  # 41
CHANNEL_MESSAGE = EventKind.CHANNEL_MESSAGE  # 42
CHANNEL_HIDE = EventKind.CHANNEL_HIDE  # 43
CHANNEL_MUTE = EventKind.CHANNEL_MUTE  # 44
BOT_CHANNEL_INVITE = 21021

RELAYS = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol/",
    "wss://relay.primal.net",
    "wss://relay.snort.social/",
]

DEFAULT_FILTERS = dict(kinds=[DM, CHANNEL_CREATE, CHANNEL_MESSAGE], limit=100)

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
class AbbotNostr:
    relay_manager = RelayManager(timeout=6)
    notices = []
    events = []

    def __init__(self, sk: str, filters_data: dict = None, author_whitelist: Optional[List[str]] = None):
        self.private_key = PrivateKey.from_hex(sk)
        self.public_key = self.private_key.public_key
        self.filters_data = filters_data or DEFAULT_FILTERS
        self.filters_list = FiltersList([Filters(**self.filters_data)])
        self.author_whitelist = author_whitelist

    @try_except
    def add_relays_and_subscribe(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)
        channel_invite_filter = Filters(
            kinds=[BOT_CHANNEL_INVITE], pubkey_refs=[self.public_key.hex()], authors=self.author_whitelist
        )
        filters = FiltersList(DEFAULT_FILTERS + [channel_invite_filter])
        self.relay_manager.add_subscription_on_all_relays(uuid.uuid4().hex, filters)
        # subscription_id = uuid.uuid1().hex
        # self.relay_manager.add_subscription_on_all_relays(subscription_id, self.filters)

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
    def create_dm(self, content: str, recipient_pubkey: str):
        dm = EncryptedDirectMessage(self.public_key.hex(), recipient_pubkey, content)
        dm.encrypt(self.private_key.hex())
        dm_event = dm.to_event()
        dm_event.sign(self.public_key.hex())
        return dm_event

    def send_greeting_to_channel(self, channel_id: str):
        event = Event(
            kind=CHANNEL_MESSAGE,
            pubkey=self.public_key.hex(),
            content=INTRODUCTION,
            tags=[["e", channel_id, RELAYS[0], "root"]],
        )
        event.sign(self.private_key.hex())
        print(event)
        self.publish_event(event)

    def publish_event(self, event):
        self.relay_manager.publish_event(event)
        self.relay_manager.run_sync()


if __name__ == "__main__":
    # abbot_nostr.add_relays_subscribe_and_run()
    # pool = abbot_nostr.get_message_pool()
    # notices = abbot_nostr.get_notices()
    # events = abbot_nostr.get_events()
    # print("pool", pool)
    # print("notices", notices)
    # print("events", events)
    abbot_nostr = AbbotNostr(os.environ["ABBOT_SEC"])
    abbot_nostr.add_relays_and_subscribe()
    for event in filter(lambda e: e.kind == BOT_CHANNEL_INVITE, abbot_nostr.poll_for_events()):
        # this outputs all valid invite events. we still need to verify that they come from
        # a specified whitelist of pubkeys, aka the atlbitlab pubkey
        # print(event)
        # search for 'e' tag that holds the channel id to join
        channel_tag: List[str] = next(filter(lambda t: t[0] == "e", event.tags))
        # print(channel_tag)s
        abbot_nostr.send_greeting_to_channel(channel_tag[1])
    # relay_manager = RelayManager(timeout=6)
    # relay_manager.add_relay("wss://relay.damus.io")
    # private_key = abbot_nostr.private_key
    # private_key_hex = private_key.hex()
    # filters = FiltersList([Filters(authors=[private_key.public_key.hex()], limit=100)])
    # subscription_id = uuid.uuid1().hex
    # relay_manager.add_subscription_on_all_relays(subscription_id, filters)
    # dm_event: Event = abbot_nostr.create_dm_event(
    #     "Secret message2! Hello world!", "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
    # )
    # dm_event.sign(private_key_hex)
    # relay_manager.publish_event(dm_event)
    # relay_manager.run_sync()
    # time.sleep(5)  # allow the messages to send
    # while relay_manager.message_pool.has_ok_notices():
    #     ok_msg = relay_manager.message_pool.get_ok_notice()
    #     print(ok_msg)
    # while relay_manager.message_pool.has_events():
    #     event_msg = relay_manager.message_pool.get_event()
    #     print(event_msg.event)


def run():
    # TODO: create nostr run fn using backend handlers
    pass
