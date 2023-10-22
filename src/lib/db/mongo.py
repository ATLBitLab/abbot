from pymongo import MongoClient
from lib.abbot.env import DATABASE_CONNECTION_STRING

client = MongoClient(host=DATABASE_CONNECTION_STRING)
