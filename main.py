#!/usr/bin/env python3

import uuid
import logging
import json
import os

import threading
import datetime as dt

import config
from dataconnect import DataConnect, DataConnectError
from xmpp_interface import XmppInterface

import web_interface

class AuthorizeRequests:

    def __init__(self):
        self.data = {}

    def add(self, jid, user_state, redirect_uri):

        while True:
            state = str(uuid.uuid4())[:8]
            if not state in self.data:
                break

        self.data[state] = {
            'jid': jid,
            'state': user_state,
            'redirect_uri': redirect_uri
        }

        return state

    def get(self, state):
        return self.data.get(state)

class Tokens:

    def __init__(self):
        self.data = {}

    def set(self, access_token, refresh_token, expires_in, idx=None):
        if idx is None:
            idx = len(self.data)
        expires_at = dt.datetime.now() + dt.timedelta(seconds=int(expires_in))
        expires_at = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        self.data[idx] = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }
        return str(idx)

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

    def __init__(self, data_connect):
        self.data_connect = data_connect
        self.tokens = Tokens()
        self.usage_points = UsagePoints()
        self.authorize_requests = AuthorizeRequests()
        self.load_state()

    def save_state(self):
        state = {
            'tokens': self.tokens.data,
            'usage_points': self.usage_points.data,
            'authorize_requests': self.authorize_requests.data
        }
        with open('state.json', 'w') as f:
            json.dump(state, f)

    def load_state(self):
        if os.path.exists('state.json'):
            with open('state.json') as f:
                state = json.load(f)
            self.tokens.data = state['tokens']
            self.usage_points.data = state['usage_points']
            self.authorize_requests.data = state['authorize_requests']

    def register_authorize_request(self, redirect_uri, duration, user_bare_jid, user_state):

        state = self.authorize_requests.add(user_bare_jid, user_state, redirect_uri)
        return self.data_connect.make_authorize_url('P1Y', state=state)

    def authorize_request_callback(self, code, state):

        authorize_request = self.authorize_requests.get(state)

        if authorize_request is None:
            return None

        res = self.data_connect.get_access_token(code=code)

        jid = authorize_request['jid']
        token_id = self.tokens.set(res['access_token'], res['refresh_token'], res['expires_in'])

        usage_points = res['usage_points_id'].split(',')

        for usage_point in usage_points:
            self.usage_points.set(jid, usage_point, token_id)

        self.xmpp_interface.notify_authorize_complete(jid, usage_points)

        return {
            'user': jid,
            'redirect_uri': authorize_request['redirect_uri'],
            'usage_points': usage_points
        }

    def get_access_token(self, jid, usage_point_id):

        user_usage_points = self.usage_points.get(jid)
        if not user_usage_points:
            return None # TODO throw

        token_id = user_usage_points.get(usage_point_id)
        if not token_id:
            return None # TODO throw

        print(token_id)

        token = self.tokens.get(token_id)

        # TODO time margin
        if dt.datetime.now() > token['expires_at']:
            print("A refresh token is needed")
            res = self.data_connect.get_access_token(refresh_token=token['refresh_token'])
            self.tokens.set(res['access_token'], res['refresh_token'], res['expires_in'], token_id)
            access_token = res['access_token']
        else:
            access_token = token['access_token']

        return access_token

    def get_consumption_load_curve(self, jid, usage_point_id, start_date, end_date):
        access_token = self.get_access_token(jid, usage_point_id)
        data = self.data_connect.get_consumption_load_curve(usage_point_id, start_date, end_date, access_token)
        return data

if __name__ == '__main__':

    data_connect = DataConnect(config.DATACONNECT_ID,
                               config.DATACONNECT_SECRET,
                               config.DATACONNECT_REDIRECT_URI,
                               sandbox=True)

    proxy = DataConnectProxy(data_connect)

    print(proxy.get_consumption_load_curve('cyril_lugan@liberasys.com', '22516914714270', '2020-05-01', '2020-05-02'))

    # Ideally use optparse or argparse to get JID,
    # password, and log level.

    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    xmpp = XmppInterface(config.XMPP_JID, config.XMPP_PASSWORD, proxy)

    proxy.xmpp_interface = xmpp # TODO this is ugly

    xmpp.connect()

    xmpp_processing = threading.Thread(target=xmpp.process)
    xmpp_processing.start()

    web_interface.data_connect_proxy = proxy # TODO this is ugly
    web_interface.app.run(host='0.0.0.0', port=443, ssl_context='adhoc')

    proxy.save_state()

    xmpp.disconnect()
