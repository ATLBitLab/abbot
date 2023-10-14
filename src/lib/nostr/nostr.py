import asyncio
import uuid
from binascii import unhexlify

from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind
from env import BOT_NPUB, BOT_PUB_HEX, BOT_SEC_HEX


class Nostr:
    def __init__(self, sec_key: str) -> None:
        assert (sec_key is not None, "Nostr secret key must be supplied")
        self.sec_key = self.BOT_SEC_HEX
        private_key = PrivateKey(unhexlify(BOT_SEC_HEX))
        public_key = private_key.public_key

    async def subscribe(self):
        relay_manager = RelayManager(timeout=2)
        for relay in self.RELAYS:
            relay_manager.add_relay(relay)
        filters = FiltersList([Filters(kinds=[EventKind.TEXT_NOTE])])
        subscription_id = uuid.uuid1().hex
        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        while relay_manager.message_pool.has_notices():
            notice_msg = relay_manager.message_pool.get_notice()
            print(notice_msg.content)
        while relay_manager.message_pool.has_events():
            event_msg = relay_manager.message_pool.get_event()
            print(event_msg.event.content)
        relay_manager.close_all_relay_connections()


"""
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
  """
