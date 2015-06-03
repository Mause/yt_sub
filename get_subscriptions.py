#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import pickle
from functools import wraps
from io import StringIO
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


def pages():
    """
    Pulled from http://stackoverflow.com/questions/30263293/
    """
    d0 = "AEIMQUYcgkosw048"
    d1 = d2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    d1c, d2c = 0, 0
    overflowSuffix = "Q"
    direction = "AA"
    d2OverflowCounter = 0
    pageSize = 50

    for i in range(1024):
        if i % pageSize == 0:
            yield (
                "C" + d1[((d1c // len(d0)) % len(d1))] +
                d0[(i % len(d0))] +
                overflowSuffix +
                direction
            )

        d1c += 1
        d2c += 1
        if d1c % (1 << 8) == 0:
            d1c = 1 << 7
        if d2c % (1 << 7) == 0:
            d2OverflowCounter += 1
            overflowSuffix = d2[d2OverflowCounter] + "E"


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
    # import ipdb
    # ipdb.set_trace()
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
def show_csv(session):
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


@app.route('/show')
@login_required
def show(session):
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
    import ipdb
    ipdb.set_trace()
    resp = redirect(url_for('index'))
    resp.delete_cookie('session')
    return resp


@app.route('/')
def index():
    return (
        redirect(url_for('show'))
        if get_session()
        else
        render_template('index.html')
    )


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == "__main__":
    Heroku().init_app(app)

    port = os.environ.get('PORT', 9000)
    app.run(debug=True, host="0.0.0.0", port=int(port))
