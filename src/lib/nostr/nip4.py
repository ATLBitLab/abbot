import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from coincurve import PublicKey
from coincurve.keys import PrivateKey
import base64
import time
from env import NOSTR_NPUB, NOSTR_PUB, NOSTR_SEC

# Assuming our_private_key and their_public_key are given as hex strings
# and text is the message you want to encrypt, given as a string.


def nip4():
    our_private_key = bytes.fromhex(NOSTR_SEC)
    their_public_key = bytes.fromhex(
        "029ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
    )
    text = "Hi, this is a test!"

    # Compute shared secret
    our_private_key_obj = PrivateKey(our_private_key)
    their_public_key_obj = PublicKey(their_public_key)
    shared_point = our_private_key_obj.ecdh(their_public_key_obj.format())
    shared_x = shared_point[:32]

    # Create an AES-256-CBC cipher using the shared secret as the key
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(shared_x), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Ensure the text is a multiple of block size by padding if necessary
    padding_length = 16 - len(text) % 16
    text += chr(padding_length) * padding_length
    text_bytes = text.encode("utf-8")

    # Encrypt the message
    encrypted_message = encryptor.update(text_bytes) + encryptor.finalize()
    encrypted_message_base64 = base64.b64encode(encrypted_message).decode("utf-8")
    iv_base64 = base64.b64encode(iv).decode("utf-8")

    # Build the event object (assuming our_pub_key is given as a hex string)
    our_pub_key = "YOUR_PUBLIC_KEY_HEX"
    event = {
        "pubkey": our_pub_key,
        "created_at": int(time.time()),
        "kind": 4,
        "tags": [["p", their_public_key.hex()]],
        "content": encrypted_message_base64 + "?iv=" + iv_base64,
    }
    print(event)
