import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from coincurve import PublicKey
from coincurve.keys import PrivateKey
import base64
import time
# import datetime
from env import NOSTR_NPUB, NOSTR_PUB, NOSTR_SEC

# Assuming sender_private_key and recip_public_key (recipient) are given as hex strings
# and text is the message you want to encrypt, given as a string.


def nip4():
    sender_private_key = bytes.fromhex(NOSTR_SEC)
    recip_public_key = bytes.fromhex(
        "029ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
    )
    text = "Hi, this is a test!"

    # Compute shared secret
    sender_private_key_obj = PrivateKey(sender_private_key)
    recip_public_key_obj = PublicKey(recip_public_key)
    shared_point = sender_private_key_obj.ecdh(recip_public_key_obj.format())
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
