#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from urllib.parse import urljoin as urljoin_bad

from rauth import OAuth2Service

from auth import CLIENT_ID, CLIENT_SECRET, PROD

urljoin = lambda *parts: urljoin_bad(parts[0], '/'.join(parts[1:]))

YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_BASE_URL = urljoin(
    'https://www.googleapis.com/',
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION
)

youtube = OAuth2Service(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    name=YOUTUBE_API_SERVICE_NAME,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    base_url=YOUTUBE_BASE_URL
)


redirect_uri = 'https://yt.mause.me' if PROD else 'http://localhost:5000'


def get_authorize_url():
    return youtube.get_authorize_url(
        scope=YOUTUBE_READ_WRITE_SCOPE,
        response_type='code',
        redirect_uri=redirect_uri + '/oauth2callback'
    )


def get_auth_session(code):
    return youtube.get_auth_session(
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri + '/oauth2callback'
        },
        decoder=lambda q: json.loads(q.decode())
    )
