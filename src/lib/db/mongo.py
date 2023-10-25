from pymongo import MongoClient
from lib.abbot.env import DATABASE_CONNECTION_STRING

client = MongoClient(host=DATABASE_CONNECTION_STRING)

nostr_db = client.get_database("nostr")
nostr_notes = nostr_db.get_collection("notes")
nostr_channels = nostr_db.get_collection("channels")

telegram_db = client.get_database("telegram")
telegram_channels = client.get_database("telegram")
