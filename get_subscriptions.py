#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import pickle
from functools import wraps
from io import StringIO
from itertools import count
from operator import itemgetter

from flask.ext.heroku import Heroku
from flask import (
    Flask, Response, redirect, request, render_template, send_from_directory,
    url_for
)

import youtube

app = Flask(__name__)


class AuthError(Exception):
    pass


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kw):
        session = get_session()

        return (
            func(session, *args, **kw)
            if session
            else
            redirect(url_for('auth'))
        )

    return wrapper


@app.route("/auth")
def auth():
    return redirect(youtube.get_authorize_url())


@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')

    session = youtube.get_auth_session(code)

    resp = redirect(url_for('index'))

    resp.set_cookie('session', pickle.dumps(session).decode('latin-1'))

    return resp


def calculate_next_page_token(page, max_result):
    page -= 1
    low = 'AEIMQUYcgkosw048'
    high = 'ABCDEFGHIJKLMNOP'
    len_low = len(low)
    len_high = len(high)

    position = page * max_result

    overflow_token = 'Q'
    if position >= 128:
        overflow_token_iteration = position // 128
        overflow_token = '%sE' % high[overflow_token_iteration]
        pass
    low_iteration = position % len_low

    # at this position the iteration starts with 'I' again (after 'P')
    if position >= 256:
        multiplier = (position // 128) - 1
        position -= 128 * multiplier
        pass
    high_iteration = (position / len_low) % len_high

    return 'C{}{}{}AA'.format(
        high[high_iteration],
        low[low_iteration],
        overflow_token
    )


pages = lambda max_result=50: (
    calculate_next_page_token(page, max_result)
    for page in count(1)
)


def paginate(func, *args, **kw):
    for page in pages():
        kw['params']['pageToken'] = page

        data = func(*args, **kw).json()
        error = data.get('error')
        if error:
            error_type = error['errors'][0]['reason']
            if error_type == 'authError':
                raise AuthError()
            else:
                raise Exception(error['messages'])

        if not data['items']:
            break

        yield from data['items']


def get_subs(session):
    # youtube.sess.inject(session)
    # return youtube.gdata.subscriptions().list(
    #     part='id,snippet,contentDetails',
    #     mine=True,
    #     maxResults=50
    # ).execute()

    return paginate(
        session.get,
        'https://www.googleapis.com/youtube/v3/subscriptions',
        params={
            'part': 'id,snippet,contentDetails',
            'mine': True,
            'maxResults': 50
        }
    )


def get_session():
    session = request.cookies.get('session')

    return (
        pickle.loads(session.encode('latin-1'))
        if session
        else None
    )


def to_csv(headers, data):
    fh = StringIO()
    writ = csv.DictWriter(fh, headers)
    writ.writeheader()
    writ.writerows(data)

    return Response(fh.getvalue(), mimetype='application/csv')


@app.route('/subscriptions.csv')
@login_required
def subscriptions_csv(session):
    items = get_subs(session)
    snippets = map(itemgetter('snippet'), items)
    snippets = sorted(snippets, key=itemgetter('title'))

    return to_csv(
        ['title', 'url'],
        (
            {
                'title': snip['title'],
                'url': 'https://www.youtube.com/channel/{}'.format(
                    snip['resourceId']['channelId']
                )
            }
            for snip in snippets
        )
    )


@app.route('/subscriptions')
@login_required
def subscriptions(session):
    try:
        items = list(get_subs(session))
    except AuthError:
        return redirect(url_for('auth'))

    return render_template(
        'subscriptions.html',
        items=sorted(items, key=lambda q: q['snippet']['title'])
    )


@app.route('/logout')
def logout():
    resp = redirect(url_for('index'))
    resp.delete_cookie('session')
    return resp


@app.route('/')
def index():
    return (
        redirect(url_for('subscriptions'))
        if get_session()
        else
        render_template('index.html')
    )


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == "__main__":
    Heroku().init_app(app)

    port = os.environ.get('PORT', 5000)
    app.run(debug=True, host="0.0.0.0", port=int(port))
