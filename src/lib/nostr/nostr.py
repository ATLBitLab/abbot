import os
import io
import json
from uuid import uuid1
from binascii import unhexlify
import IPython
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind

from lib.env import NOSTR_SEC

private_key = PrivateKey(unhexlify(NOSTR_SEC))
public_key = private_key.public_key

NOSTR_EVENTS_FILE = os.path.abspath(os.path.join("data", "events.jsonl"))
RELAYS = [
   'wss://eden.nostr.land',
   'wss://nostr.fmt.wiz.biz',
   'wss://relay.damus.io',
   'wss://nostr-pub.wellorder.net',
   'wss://relay.nostr.info',
   'wss://offchain.pub',
   'wss://nos.lol',
   'wss://brb.io',
   'wss://relay.snort.social',
   'wss://relay.current.fyi',
   'wss://nostr.relayer.se',
]

def get_note_ids():
  notes_jl = io.open(NOSTR_EVENTS_FILE, "r")
  seen = set()
  for note in notes_jl.readlines():
    note_obj = json.loads(note)
    seen.add(note_obj.get('id'))
  return seen

def nostr_main():
    notes_jl = io.open(NOSTR_EVENTS_FILE, "a")
    seen = get_note_ids()
    relay_manager = RelayManager(timeout=2)
    for relay in RELAYS:
      relay_manager.add_relay(relay)
    filters = FiltersList([Filters(kinds=[EventKind.TEXT_NOTE])])
    subscription_id = uuid1().hex
    relay_manager.add_subscription_on_all_relays(subscription_id, filters)
    relay_manager.run_sync()
    while relay_manager.message_pool.has_events():
      msg = relay_manager.message_pool.get_event()
      event_id = msg.event.id
      if event_id not in seen:
        seen.add(event_id)
        notes_jl.write(json.dumps(msg.event.to_dict()))
        notes_jl.write("\n")
    notes_jl.close()
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