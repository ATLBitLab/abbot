import os
import uuid
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.event import Event
from typing import List, Optional

DM = EventKind.ENCRYPTED_DIRECT_MESSAGE  # 4
CHANNEL_CREATE = EventKind.CHANNEL_CREATE  # 40
CHANNEL_META = EventKind.CHANNEL_META  # 41
CHANNEL_MESSAGE = EventKind.CHANNEL_MESSAGE  # 42
CHANNEL_HIDE = EventKind.CHANNEL_HIDE  # 43
CHANNEL_MUTE = EventKind.CHANNEL_MUTE  # 44
BOT_CHANNEL_INVITE = 21021

RELAYS = [
    "wss://booger.pro",
    "wss://nos.lol/",
    "wss://relay.bitcoinpark.com/",
    "wss://relay.damus.io",
    "wss://nostr-pub.wellorder.net/",
    "wss://relay.primal.net",
    "wss://nostr.atlbitlab.com/",
    "wss://relay.snort.social/",
]

DEFAULT_FILTERS = [Filters(kinds=[DM, CHANNEL_CREATE, CHANNEL_MESSAGE], limit=100)]

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

class AbbotFilters:
    def __init__(self, filter_data: list):
        self.Filters = Filters(filter_data)
        """
            kinds: Optional[List[EventKind]] = None
            authors: Optional[List[str]] = None
        """


class AbbotNostr:
    relay_manager = RelayManager(timeout=6)
    notices = []
    events = []

    def __init__(self, sec_key: str, author_whitelist: Optional[List[str]] = None):
        self.sec_key = sec_key
        self.private_key = PrivateKey.from_hex(sec_key)
        self.public_key = self.private_key.public_key
        self.author_whitelist = author_whitelist

    def add_relays_subscribe_and_run(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)

        channel_invite_filter = Filters(
            kinds=[BOT_CHANNEL_INVITE],
            pubkey_refs=[self.public_key.hex()],
            authors=self.author_whitelist
        )
        filters = FiltersList(DEFAULT_FILTERS + [channel_invite_filter])
        self.relay_manager.add_subscription_on_all_relays(uuid.uuid4().hex, filters)
        self.relay_manager.run_sync()

    def get_message_pool(self):
        return self.relay_manager.message_pool

    def get_notices(self):
        while self.relay_manager.message_pool.has_notices():
            notice_msg = self.relay_manager.message_pool.get_notice()
            print(notice_msg)
            self.notices.append(notice_msg)
        return self.notices

    def get_events(self):
        while self.relay_manager.message_pool.has_events():
            event = self.relay_manager.message_pool.get_event().event
            if event.verify():
                yield event

    def unsubscribe(self, url, id: str):
        self.relay_manager.close_subscription_on_relay(url, id)

    def disconnect_from_relays(self):
        self.relay_manager.close_connections()

    def create_dm_event(self, content: str, recipient_pubkey: str):
        dm = EncryptedDirectMessage(self.public_key, recipient_pubkey, content)
        dm.encrypt(self.private_key_hex)
        dm_event = dm.to_event()
        return dm_event

    def send_greeting_to_channel(self, channel_id: str):
        event = Event(
            kind=CHANNEL_MESSAGE,
            pubkey=self.public_key.hex(),
            content=INTRODUCTION,
            tags=[['e', channel_id, RELAYS[0], 'root']]
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
    abbot_nostr.add_relays_subscribe_and_run()
    for event in filter(lambda e: e.kind == BOT_CHANNEL_INVITE, abbot_nostr.get_events()):
        # this outputs all valid invite events. we still need to verify that they come from
        # a specified whitelist of pubkeys, aka the atlbitlab pubkey
        # print(event)
        # search for 'e' tag that holds the channel id to join
        channel_tag: List[str] = next(filter(lambda t: t[0] == 'e', event.tags))
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
