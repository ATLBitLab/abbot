from nostr.key import PrivateKey
from lib.env import NOSTR_SEC

private_key = PrivateKey(NOSTR_SEC)
public_key = private_key.public_key
print(private_key)
print(public_key)