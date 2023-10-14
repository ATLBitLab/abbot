import time
import uuid
from binascii import unhexlify

from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind


from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.key import PrivateKey
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from coincurve import PublicKey
from coincurve.keys import PrivateKey
import base64
import time
from env import NOSTR_NPUB, NOSTR_PUB, NOSTR_SEC


class Nostr:
    RELAYS = [
        "wss://eden.nostr.land",
        "wss://nostr.fmt.wiz.biz",
        "wss://relay.damus.io",
        "wss://nostr-pub.wellorder.net",
        "wss://relay.nostr.info",
        "wss://offchain.pub",
        "wss://nos.lol",
        "wss://brb.io",
        "wss://relay.snort.social",
        "wss://relay.current.fyi",
        "wss://nostr.relayer.se",
    ]

    def __init__(self, sec_key):
        assert (sec_key is not None, "Nostr secret key must be supplied")
        self.sec_key = sec_key
        private_key = PrivateKey(unhexlify(sec_key))
        public_key = private_key.public_key

    def subscribe(self):
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

    def sendDM(self):
        sender_private_key = bytes.fromhex(NOSTR_SEC)
        recip_public_key = bytes.fromhex(
            "029ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
        )
        text = "Hi, this is a test!"

        # Compute shared secret
        sender_private_key_obj = PrivateKey(sender_private_key)
        recip_public_key_obj = PublicKey(recip_public_key)
        shared_point = sender_private_key_obj.ecdh(
            recip_public_key_obj.format())
        shared_x = shared_point[:32]

        # Create an AES-256-CBC cipher using the shared secret as the key
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(shared_x), modes.CBC(iv),
                        backend=default_backend())
        encryptor = cipher.encryptor()

        # Ensure the text is a multiple of block size by padding if necessary
        padding_length = 16 - len(text) % 16
        text += chr(padding_length) * padding_length
        text_bytes = text.encode("utf-8")

        # Encrypt the message
        encrypted_message = encryptor.update(text_bytes) + encryptor.finalize()
        encrypted_message_base64 = base64.b64encode(
            encrypted_message).decode("utf-8")
        iv_base64 = base64.b64encode(iv).decode("utf-8")

        # Build the event object (assuming sender_pub_key is given as a hex string)
        sender_pub_key = NOSTR_PUB

        # UTC timezone but date/time should be adjusted according to where the current user is
        timestamp = time.time()
        # local_datetime = datetime.datetime.fromtimestamp(timestamp)
        event = {
            "pubkey": sender_pub_key,
            "created_at": int(timestamp),
            "kind": 4,
            "tags": [["p", recip_public_key.hex()]],
            "content": encrypted_message_base64 + "?iv=" + iv_base64,
        }
        print(event)
        print(timestamp)
