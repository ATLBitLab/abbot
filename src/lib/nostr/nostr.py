import os
import uuid
import time
import base64
import asyncio
from binascii import unhexlify

from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.event import EventKind

from pynostr.encrypted_dm import EncryptedDirectMessage

from coincurve import PublicKey
from coincurve.keys import PrivateKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from lib.logger import debug
from bot_constants import RELAYS, BOT_PUB_HEX, BOT_NPUB

(
    TEXT_NOTE,
    ENCRYPTED_DIRECT_MESSAGE,
    CHANNEL_CREATE,
    CHANNEL_META,
    CHANNEL_MESSAGE,
    CHANNEL_HIDE,
    CHANNEL_MUTE,
) = EventKind


class Nostr:
    from bot_env import BOT_SEC_HEX

    NONNI_PUB = "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"

    def __init__(self) -> None:
        fn = "__init__ =>"
        assert (self.BOT_SEC_HEX is not None, "Nostr secret key must be supplied")
        private_key = PrivateKey(unhexlify(self.BOT_SEC_HEX))
        self.public_key = private_key.public_key
        self.relay_manager = RelayManager(timeout=2)
        debug(f"{fn} public_key={self.public_key}")

    async def subscribe(self):
        for relay in RELAYS:
            self.relay_manager.add_relay(relay)
        filters = FiltersList(
            [
                Filters(
                    kinds=[
                        EventKind.TEXT_NOTE,
                        EventKind.ENCRYPTED_DIRECT_MESSAGE,
                        EventKind.CHANNEL_CREATE,
                        EventKind.CHANNEL_META,
                        EventKind.CHANNEL_MESSAGE,
                        EventKind.CHANNEL_HIDE,
                        EventKind.CHANNEL_MUTE,
                    ]
                )
            ]
        )
        subscription_id = uuid.uuid1().hex
        self.relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        self.subscribe_notices()
        self.subscribe_events()

    async def subscribe_notices(self):
        while self.relay_manager.message_pool.has_notices():
            content, url = self.relay_manager.message_pool.get_notice()
            print(f"content={content} url={url}")

    async def subscribe_events(self):
        while self.relay_manager.message_pool.has_events():
            event, subscription_id, url = self.relay_manager.message_pool.get_event()
        print(f"event={event} subscription_id={subscription_id} url={url}")

    def send_dm(self, message_text: str):
        sender_private_key = bytes.fromhex(self.BOT_SEC_HEX)
        recip_public_key = bytes.fromhex(self.NONNI_PUB)
        # Compute shared secret
        sender_private_key_obj = PrivateKey(sender_private_key)
        recip_public_key_obj = PublicKey(recip_public_key)
        shared_point = sender_private_key_obj.ecdh(recip_public_key_obj.format())
        shared_x = shared_point[:32]
        # Create an AES-256-CBC cipher using the shared secret as the key
        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(shared_x), modes.CBC(iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()
        # Ensure the text is a multiple of block size by padding if necessary
        padding_length = 16 - len(self.MESSAGE_TEXT) % 16
        self.MESSAGE_TEXT += chr(padding_length) * padding_length
        text_bytes = self.MESSAGE_TEXT.encode("utf-8")
        # Encrypt the message
        encrypted_message = encryptor.update(text_bytes) + encryptor.finalize()
        encrypted_message_base64 = base64.b64encode(encrypted_message).decode("utf-8")
        iv_base64 = base64.b64encode(iv).decode("utf-8")
        # Build the event object (assuming sender_pub_key is given as a hex string)
        # UTC timezone but date/time should be adjusted according to where the current user is
        timestamp = time.time()
        # local_datetime = datetime.datetime.fromtimestamp(timestamp)
        event = {
            "pubkey": BOT_PUB_HEX,
            "created_at": int(timestamp),
            "kind": 4,
            "tags": [["p", recip_public_key.hex()]],
            "content": encrypted_message_base64 + "?iv=" + iv_base64,
        }
        print(event)
        print(timestamp)
