#!/usr/bin/env python3

import uuid
import logging
import json
import os
import asyncio
import bleach
import unittest

import threading
import datetime as dt

from dataconnect import DataConnect, DataConnectError
from xmpp_interface import XmppInterface

import web_interface.app

class AuthorizeDescriptions:

    def __init__(self):
        self.data = {}

    # TODO rename service to desciption when switching to database
    def add(self, jid, name, service, logo_url):
        while True:
            uid = str(uuid.uuid4())[:8]
            if not uid in self.data:
                break

        service = bleach.clean(service, bleach.sanitizer.ALLOWED_TAGS + ['p', 'br'])

        self.data[uid] = {
            'jid': jid,
            'name': name,
            'service': service,
            'logo_url': logo_url
        }

        return uid

    def get(self, uid):
        return self.data.get(uid)

class AuthorizeDescriptionsTest(unittest.TestCase):

    DEFAULT_JID = 'proxy-client@elec-expert.net'
    DEFAULT_NAME = 'Elec Expert'

    def setUp(self):
        self.authorize_descriptions = AuthorizeDescriptions()

    def test_sanitize_description(self):
        html_desc = 'an <script>evil()</script> example'
        html_desc_escaped = 'an &lt;script&gt;evil()&lt;/script&gt; example'
        uid = self.authorize_descriptions.add(self.DEFAULT_JID, self.DEFAULT_NAME, html_desc)
        self.assertEqual(self.authorize_descriptions.get(uid)['service'], html_desc_escaped)

    def test_p_and_a_tags_are_not_sanitized(self):
        html_desc = '<p>Description with <a href="#">link</a>.</p>'
        uid = self.authorize_descriptions.add(self.DEFAULT_JID, self.DEFAULT_NAME, html_desc)
        self.assertEqual(self.authorize_descriptions.get(uid)['service'], html_desc)

class AuthorizeRequests:

    def __init__(self):
        self.data = {}

    def add(self, jid, user_state, redirect_uri, test_client_id=None):

        # Test client id should be a str between '0' and '9'
        if not isinstance(test_client_id, str) or len(test_client_id) != 1:
            test_client_id=None

        while True:
            state = str(uuid.uuid4())[:8]
            if test_client_id is not None:
                state = state + test_client_id
            if not state in self.data:
                break

        self.data[state] = {
            'jid': jid,
            'state': user_state,
            'redirect_uri': redirect_uri,
            'is_sandbox': test_client_id is not None
        }

        return state

    def get(self, state):
        return self.data.get(state)

class Tokens:

    def __init__(self):
        self.data = {}

    def set(self, access_token, refresh_token, expires_in, is_sandbox, idx=None):
        if idx is None:
            idx = str(len(self.data))
        expires_at = dt.datetime.now() + dt.timedelta(seconds=int(expires_in))
        expires_at = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        self.data[idx] = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'is_sandbox': is_sandbox
        }
        return idx

    def get(self, idx):
        value = self.data.get(idx).copy()
        if value is not None:
            value['expires_at'] = dt.datetime.strptime(value['expires_at'], '%Y-%m-%d %H:%M:%S')
        return value

class UsagePoints:

    def __init__(self):
        self.data = {}

    def set(self, jid, usage_point, token_id):
        if not jid in self.data:
            self.data[jid] = {}
        self.data[jid][usage_point] = token_id

    def get(self, jid):
        return self.data.get(jid)

class DataConnectProxy:

    def __init__(self, data_connect_prod, data_connect_sandbox, web_interface_base_uri):
        self.data_connect_prod = data_connect_prod
        self.data_connect_sandbox = data_connect_sandbox
        self.web_interface_base_uri = web_interface_base_uri
        self.tokens = Tokens()
        self.usage_points = UsagePoints()
        self.authorize_descriptions = AuthorizeDescriptions()
        self.authorize_requests = AuthorizeRequests()
        self.load_state()

    def save_state(self):
        state = {
            'tokens': self.tokens.data,
            'usage_points': self.usage_points.data,
            'authorize_descriptions': self.authorize_descriptions.data,
            'authorize_requests': self.authorize_requests.data
        }
        with open('state.json', 'w') as f:
            json.dump(state, f)

    def load_state(self):
        if os.path.exists('state.json'):
            with open('state.json') as f:
                state = json.load(f)
            self.tokens.data = state.get('tokens', {})
            self.usage_points.data = state.get('usage_points', {})
            self.authorize_descriptions.data = state.get('authorize_descriptions', {})
            self.authorize_requests.data = state.get('authorize_requests', {})

    def get_data_connect(self, sandbox):
        if sandbox:
            return self.data_connect_sandbox
        else:
            return self.data_connect_prod


    def register_authorize_description(self, jid, name, service, logo_url):

        uid = self.authorize_descriptions.add(jid, name, service, logo_url)
        return os.path.join(self.web_interface_base_uri, f'authorize?id={uid}')

    def register_authorize_request(self, redirect_uri, duration, user_bare_jid, user_state, test_client_id=None):

        state = self.authorize_requests.add(user_bare_jid, user_state, redirect_uri, test_client_id)
        is_sandbox = test_client_id is not None
        return self.get_data_connect(is_sandbox).make_authorize_url('P1Y', state=state)

    def authorize_request_callback(self, code, state):

        authorize_request = self.authorize_requests.get(state)

        if authorize_request is None:
            return None

        is_sandbox = authorize_request['is_sandbox']

        res = self.get_data_connect(is_sandbox).get_access_token(code=code)

        jid = authorize_request['jid']
        token_id = self.tokens.set(res['access_token'], res['refresh_token'], res['expires_in'], is_sandbox)

        logging.info(f"New refresh token: {res['usage_points_id']}, {res['refresh_token']}")

        usage_points = res['usage_points_id'].split(',')

        for usage_point in usage_points:
            self.usage_points.set(jid, usage_point, token_id)

        self.xmpp_interface.notify_authorize_complete(jid, usage_points, authorize_request['state'])

        return {
            'user': jid,
            'redirect_uri': authorize_request['redirect_uri'],
            'usage_points': usage_points
        }

    # TODO throw DataConnectProxyErrors
    def get_access_token(self, jid, usage_point_id):

        user_usage_points = self.usage_points.get(jid)
        if not user_usage_points:
            raise DataConnectError(f'User {jid} is not allowed to access {usage_point_id}')

        token_id = user_usage_points.get(usage_point_id)
        if not token_id:
            raise DataConnectError(f'User {jid} is not allowed to access {usage_point_id}')

        token = self.tokens.get(token_id)
        is_sandbox = token['is_sandbox']

        # TODO time margin
        if dt.datetime.now() > token['expires_at']:
            logging.info(f"A refresh token is needed")
            res = self.get_data_connect(is_sandbox).get_access_token(refresh_token=token['refresh_token'])
            logging.info(f"Update refresh token: {usage_point_id}, {token['refresh_token']} -> {res['refresh_token']}")
            self.tokens.set(res['access_token'], res['refresh_token'], res['expires_in'], is_sandbox, token_id)
            access_token = res['access_token']
        else:
            access_token = token['access_token']

        return access_token, is_sandbox

    def get_load_curve(self, direction, jid, usage_point_id, start_date, end_date):
        access_token, is_sandbox = self.get_access_token(jid, usage_point_id)
        data = self.get_data_connect(is_sandbox).get_load_curve(direction, usage_point_id, start_date, end_date, access_token)
        return data

    def get_daily(self, direction, jid, usage_point_id, start_date, end_date):
        access_token, is_sandbox = self.get_access_token(jid, usage_point_id)
        data = self.get_data_connect(is_sandbox).get_daily(direction, usage_point_id, start_date, end_date, access_token)
        return data

if __name__ == '__main__':

    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('conf', help="Configuration file (typically private/*.conf.json)")
    parser.add_argument('--unittest', action='store_true', help="Run unit tests (for this file only)")
    args = parser.parse_args()

    if args.unittest:
        unittest.main(argv=sys.argv[:1])
        exit()

    with open(args.conf, 'r') as f:
        CONF = json.load(f)['proxy']


    data_connect = DataConnect(CONF['data_connect']['production']['app_id'],
                               CONF['data_connect']['production']['app_secret'],
                               CONF['data_connect']['production']['redirect_uri'],
                               sandbox=False)

    data_connect_sandbox = DataConnect(CONF['data_connect']['sandbox']['app_id'],
                                       CONF['data_connect']['sandbox']['app_secret'],
                                       CONF['data_connect']['sandbox']['redirect_uri'],
                                       sandbox=True)

    proxy = DataConnectProxy(data_connect, data_connect_sandbox, CONF['web_interface']['base_uri'])

    # Ideally use optparse or argparse to get JID,
    # password, and log level.

    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    xmpp = XmppInterface(CONF['xmpp']['full_jid'], CONF['xmpp']['password'],
                         proxy.register_authorize_description,
                         proxy.get_load_curve,
                         proxy.get_daily)

    proxy.xmpp_interface = xmpp # TODO this is ugly
    web_interface.app.data_connect_proxy = proxy # TODO this is ugly

    # I don't really understand what is going on with asyncio
    # Got web + xmpp example on
    # https://gitlab.collabora.com/sysadmin/csp-reports-bot/-/blob/master/csp.py

    loop = asyncio.get_event_loop()
    http = loop.run_until_complete(
        web_interface.app.start(),
    )

    xmpp.connect()
    try:
        xmpp.process()
    except KeyboardInterrupt:
        xmpp.disconnect()
        xmpp.process(forever=False)
    finally:
        proxy.save_state()
