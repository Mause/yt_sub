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


EXCEPTIONS = {'authError': AuthError}


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


def paginate(func, *args, **kw):
    kw['params']['pageToken'] = None
    data = {'nextPageToken'}

    while 'nextPageToken' in data:
        data = func(*args, **kw).json()
        error = data.get('error')

        for error in data.get('error', {}).get('errors', []):
            error_type = EXCEPTIONS.get(error['reason'], Exception)

            raise error_type(error['messages'])

        kw['params']['pageToken'] = data.get('nextPageToken')

        yield from data['items']


def get_subs(session):
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
