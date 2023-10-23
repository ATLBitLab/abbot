from binascii import unhexlify
import ssl
import time
import os
import uuid
import IPython
from pynostr.key import PrivateKey, PublicKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.event import Event

from lib.abbot.exceptions.abbot_exception import try_except

DM = EventKind.ENCRYPTED_DIRECT_MESSAGE  # 4
CHANNEL_CREATE = EventKind.CHANNEL_CREATE  # 40
CHANNEL_META = EventKind.CHANNEL_META  # 41
CHANNEL_MESSAGE = EventKind.CHANNEL_MESSAGE  # 42
CHANNEL_HIDE = EventKind.CHANNEL_HIDE  # 43
CHANNEL_MUTE = EventKind.CHANNEL_MUTE  # 44

RELAYS = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol/",
    "wss://relay.primal.net",
    "wss://relay.snort.social/",
]

"""
ids: List[str] | None = None,
kinds: List[EventKind] | None = None,
authors: List[str] | None = None,
since: int | None = None,
until: int | None = None,
event_refs: List[str] | None = None,
pubkey_refs: List[str] | None = None,
limit: int | None = None

self.ids: [str] | None = try_get(filter, data)
self.kinds: [EventKind] | None = try_get(filter, data)
self.authors: [str] | None = try_get(filter, data)
self.since: int | None = try_get(filter, data)
self.until: int | None = try_get(filter, data)
self.event_refs: [str] | None = try_get(filter, data)
self.pukkey_refs: [str] | None = try_get(filter, data)
self.limit: int | None = try_get(filter, data)
"""


class AbbotFilters:
    def __init__(self, filter_data: dict):
        filters_dict: dict = dict()
        # filter_data_items: dict = zip(filter_data.keys(), filter_data.values())
        for filter, data in zip(filter_data.keys(), filter_data.values()):
            if not data:
                continue
            filters_dict[filter] = data
        self.subscription_filters = FiltersList([Filters(**dict)])

    def get_filters_list(self) -> FiltersList:
        return self.subscription_filters


@try_except
class AbbotNostr(AbbotFilters):
    relay_manager = RelayManager(timeout=6)
    notices = []
    events = []

    def __init__(self, sk: str, filter_data: dict):
        self.private_key = PrivateKey(unhexlify(sk))
        self.private_key_hex = self.private_key.hex()
        self.public_key = self.private_key.public_key
        abbot_filters = AbbotFilters(filter_data)
        self.filters = abbot_filters.get_filters_list()

    @try_except
    def add_relays_and_subscribe(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)
        subscription_id = uuid.uuid1().hex
        self.relay_manager.add_subscription_on_all_relays(subscription_id, self.filters)

    @try_except
    def run_relay_sync(self):
        self.relay_manager.run_sync()

    @try_except
    def get_message_pool(self):
        return self.relay_manager.message_pool

    @try_except
    def poll_for_notices(self):
        while self.relay_manager.message_pool.has_notices():
            notice_msg = self.relay_manager.message_pool.get_notice()
            print(notice_msg)
            self.notices.append(notice_msg)
        return self.notices

    @try_except
    def poll_for_events(self):
        while self.relay_manager.message_pool.has_events():
            event_msg = self.relay_manager.message_pool.get_event()
            print(event_msg)
        return self.events

    @try_except
    def get_events(self):
        return self.relay_manager.message_pool.events

    @try_except
    def get_notices(self):
        return self.relay_manager.message_pool.notices

    @try_except
    def unsubscribe(self, url, id: str):
        self.relay_manager.close_subscription_on_relay(url, id)

    @try_except
    def disconnect_from_relays(self):
        self.relay_manager.close_connections()

    @try_except
    def create_dm(self, content: str, recipient_pubkey: str):
        dm = EncryptedDirectMessage(self.public_key.hex(), recipient_pubkey, content)
        dm.encrypt(self.private_key_hex)
        dm_event = dm.to_event()
        dm_event.sign(self.public_key.hex())
        return dm_event

    @try_except
<<<<<<< Updated upstream
    def decrypt_dm(self, content: str, recipient_pubkey: str):
        dm = EncryptedDirectMessage(self.public_key.hex(), recipient_pubkey, content)
        dm.encrypt(self.private_key_hex)
        dm_event = dm.to_event()
        dm_event.sign(self.public_key.hex())
        return dm_event

    @try_except
    def send_dm(self, content: str, recipient_pubkey: str):
        dm_event: Event = self.create_dm(content, recipient_pubkey)
        self.add_relays_and_subscribe()
        self.relay_manager.publish_event(dm_event)
        self.run_relay_sync()
        time.sleep(5)
=======
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

    @try_except
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


@try_except
def run_nostr():
    # TODO: create nostr run fn using backend handlers
    pass
>>>>>>> Stashed changes
