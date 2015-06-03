import os
import json

try:
    with open('auth.json') as fh:
        data = json.load(fh)
    PROD = False
except FileNotFoundError:
    data = os.environ
    PROD = True

CLIENT_ID = data['CLIENT_ID']
CLIENT_SECRET = data['CLIENT_SECRET']
