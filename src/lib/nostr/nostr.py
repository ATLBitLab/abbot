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

from dotenv import load_dotenv

DM = EventKind.ENCRYPTED_DIRECT_MESSAGE  # 4
CHANNEL_CREATE = EventKind.CHANNEL_CREATE  # 40
CHANNEL_META = EventKind.CHANNEL_META  # 41
CHANNEL_MESSAGE = EventKind.CHANNEL_MESSAGE  # 42
CHANNEL_HIDE = EventKind.CHANNEL_HIDE  # 43
CHANNEL_MUTE = EventKind.CHANNEL_MUTE  # 44

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
    filters = FiltersList([Filters(kinds=[CHANNEL_MESSAGE], limit=100)])
    # filters = FiltersList([Filters(authors=[private_key.public_key.hex()], limit=100)])
    filters_list = []  # FiltersList()
    filters = kinds = [DM, CHANNEL_CREATE, CHANNEL_MESSAGE]  # Filters()
    #

    def __init__(self, sec_key):
        self.sec_key = sec_key
        self.private_key = PrivateKey(unhexlify(sec_key))
        self.private_key_hex = self.private_key.hex()
        self.public_key = self.private_key.public_key
        # self.filters = filters

    def add_relays_subscribe_and_run(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)
        subscription_id = uuid.uuid1().hex
        self.relay_manager.add_subscription_on_all_relays(
            subscription_id, self.filters)
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
            event_msg = self.relay_manager.message_pool.get_event()
            print(event_msg)
        return self.events

    def get_events(self):
        return self.relay_manager.message_pool.events

    def unsubscribe(self, url, id: str):
        self.relay_manager.close_subscription_on_relay(url, id)

    def disconnect_from_relays(self):
        self.relay_manager.close_connections()

    def create_dm_event(self, content: str, recipient_pubkey: str):
        dm = EncryptedDirectMessage(self.public_key, recipient_pubkey, content)
        dm.encrypt(self.private_key_hex)
        dm_event = dm.to_event()
        return dm_event

    def publish_event(self, event):
        self.relay_manager.publish_event(event)
        self.add_relays_subscribe_and_run()


if __name__ == "__main__":
    # abbot_nostr.add_relays_subscribe_and_run()
    # pool = abbot_nostr.get_message_pool()
    # notices = abbot_nostr.get_notices()
    # events = abbot_nostr.get_events()
    # print("pool", pool)
    # print("notices", notices)
    # print("events", events)

    load_dotenv()
    # print(os.environ["BOT_NOSTR_SK"])
    abbot_nostr = AbbotNostr(os.environ["BOT_NOSTR_SK"])
    relay_manager = RelayManager(timeout=6)
    relay_manager.add_relay("wss://relay.damus.io")
    private_key = abbot_nostr.private_key
    private_key_hex = private_key.hex()
    filters = FiltersList(
        [Filters(authors=[private_key.public_key.hex()], limit=100)])
    subscription_id = uuid.uuid1().hex
    relay_manager.add_subscription_on_all_relays(subscription_id, filters)
    dm_event: Event = abbot_nostr.create_dm_event(
        "Secret message2! Hello world!", "96ceb617eb41bfc4c45d383fe9c9d8e729cb24b71cd947faa234e22a23e59bfa"
    )
    dm_event.sign(private_key_hex)
    relay_manager.publish_event(dm_event)
    relay_manager.run_sync()
    time.sleep(5)  # allow the messages to send
    while relay_manager.message_pool.has_ok_notices():
        ok_msg = relay_manager.message_pool.get_ok_notice()
        print(ok_msg)
    while relay_manager.message_pool.has_events():
        event_msg = relay_manager.message_pool.get_event()
        print(event_msg.event)
