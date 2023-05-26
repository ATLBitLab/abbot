import json
from env import MESSAGE_LOG_FILE

f = open(MESSAGE_LOG_FILE, "r")
for line in f.readlines():
    print('line', line)
    message = json.loads(line)
    print(message)