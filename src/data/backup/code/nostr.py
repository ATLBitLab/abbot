abbot_nostr = AbbotNostr(BOT_NOSTR_SK)
# abbot_nostr.add_relays_and_subscribe()
# abbot_nostr.run_relay_sync()
# pool = abbot_nostr.get_message_pool()
# notices = abbot_nostr.get_notices()
# events = abbot_nostr.get_events()
# print("pool", pool)
# print("notices", notices)
# print("events", events)

ABBOT_PUB = "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c"
BRYAN_PUB = "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
MSG_FROM_BRYAN_TO_ABBOT = "WuNx/mLdkjhas7A3JI59Eg==?iv=LfVClj/9AS8hLQ8+PY0MgA=="
enc_dm = EncryptedDirectMessage(
    ABBOT_PUB,
    BRYAN_PUB,
    encrypted_message=MSG_FROM_BRYAN_TO_ABBOT,
)
enc_dm.decrypt(BOT_NOSTR_SK)
message = enc_dm.cleartext_content
print(f"bryan said: {message}")
MSG_FROM_ABBOT_TO_BRYAN = "8qyjvmgIdfuUo5hxPjk+aQ==?iv=HecDrNIJXVs4Cr2Ibp3BtA=="
enc_dm = EncryptedDirectMessage(
    ABBOT_PUB,
    BRYAN_PUB,
    encrypted_message=MSG_FROM_ABBOT_TO_BRYAN,
)
enc_dm.decrypt(BOT_NOSTR_SK)
message = enc_dm.cleartext_content
print(f"abbot said: {message}")
IPython.embed()
