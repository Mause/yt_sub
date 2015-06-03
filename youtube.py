#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from rauth import OAuth2Service

from auth import CLIENT_ID, CLIENT_SECRET, PROD


youtube = OAuth2Service(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    name='youtube',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    base_url='https://www.googleapis.com/youtube/v3/'
)


redirect_uri = 'http://yt.mause.me' if PROD else 'http://localhost:5000'

get_authorize_url = lambda: youtube.get_authorize_url(
    scope='https://www.googleapis.com/auth/youtube',
    response_type='code',
    redirect_uri=redirect_uri + '/oauth2callback'
)

get_auth_session = lambda code: youtube.get_auth_session(
    data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri + '/oauth2callback'
    },
    decoder=lambda q: json.loads(q.decode())
)


# import requests
# from apiclient.discovery import build

# times = 0


# class RequestsSessionWrapper():
#     class Response():
#         def __init__(self, r):
#             self.r = r

#         @property
#         def status(self):
#             return self.r.status_code

#     def __init__(self):
#         self.session = requests

#     def inject(self, session):
#         self.session = session

#     def request(self, url, method='GET', **kw):
#         if 'body' in kw:
#             kw['data'] = kw.pop('body')
#         r = self.session.request(method, url, **kw)

#         if 'error' in r.json():
#             from pprint import pprint
#             pprint(r.json())

#         return self.Response(r), r.content


# sess = RequestsSessionWrapper()
# gdata = build('youtube', 'v3', http=sess)
