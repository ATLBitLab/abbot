from lib.env import NOSTR_SEC
from uuid import uuid1
from binascii import unhexlify
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind

private_key = PrivateKey(unhexlify(NOSTR_SEC))
public_key = private_key.public_key

def nostr_main():
    relay_manager = RelayManager(timeout=2)
    relay_manager.add_relay('wss://eden.nostr.land')
    relay_manager.add_relay('wss://nostr.fmt.wiz.biz')
    relay_manager.add_relay('wss://relay.damus.io')
    relay_manager.add_relay('wss://nostr-pub.wellorder.net')
    relay_manager.add_relay('wss://relay.nostr.info')
    relay_manager.add_relay('wss://offchain.pub')
    relay_manager.add_relay('wss://nos.lol')
    relay_manager.add_relay('wss://brb.io')
    relay_manager.add_relay('wss://relay.snort.social')
    relay_manager.add_relay('wss://relay.current.fyi')
    relay_manager.add_relay('wss://nostr.relayer.se')
    filters = FiltersList([Filters(kinds=[EventKind.TEXT_NOTE], limit=100)])
    subscription_id = uuid1().hex
    relay_manager.add_subscription_on_all_relays(subscription_id, filters)
    relay_manager.run_sync()

    while relay_manager.message_pool.has_notices():
        notice_msg = relay_manager.message_pool.get_notice()
        print('notice_msg.content', notice_msg.content)
    while relay_manager.message_pool.has_events():
        event_msg = relay_manager.message_pool.get_event()
        print('event_msg.event.content', event_msg.event.content)
    relay_manager.close_all_relay_connections()

'''
Reply to a note

from pynostr.event import Event
reply = Event(
  content="Sounds good!",
)
# create 'e' tag reference to the note you're replying to
reply.add_event_ref(original_note_id)
# create 'p' tag reference to the pubkey you're replying to
reply.add_pubkey_ref(original_note_author_pubkey)
reply.sign(private_key.hex())

Send a DM

from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.key import PrivateKey
private_key = PrivateKey()
recipient_pubkey = PrivateKey().public_key.hex()
dm = EncryptedDirectMessage()
dm.encrypt(private_key.hex(),
  recipient_pubkey=recipient_pubkey,
  cleartext_content="Secret message!"
)
dm_event = dm.to_event()
dm_event.sign(private_key.hex())
'''