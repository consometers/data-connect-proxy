#!/usr/bin/env python3

import threading
import time

from flask import Flask, abort, jsonify, request, abort, redirect

from dataconnect import DataConnect, DataConnectError
import config

app = Flask(__name__)

class Pipeline():

    def __init__(self):
        self.serial_reader = BackgroundSerialReader(self.on_new_data)
        self.lock = threading.Lock()

    def on_new_data(self, data):
        data = self.data_processing.process(data)
        with self.lock:
            self.latest_data = data

    def start(self):
        self.serial_reader.start()

    def stop(self):
        self.serial_reader.interrupt()

data_connect_proxy = None

@app.route('/')
def authorize_redirect():

    if 'code' in request.values:
        code = request.values['code']
    else:
        abort(500, description=f"'code' parameter is required")

    if 'state' in request.values:
        state = request.values['state']
    else:
        state = None

    try:
        ret = data_connect_proxy.authorize_request_callback(code, state)
    except DataConnectError as e:
        return abort(500, description=str(e))

    # TODO use exception instead
    if ret is None:
        return None

    if ret['redirect_uri']:
        # TODO check code to prevent caching
        # (maybe that was the cause of the bug in the enedis portal)
        return redirect(ret['redirect_uri'], code=302)
    else:
        return f'Access to usage points {ret["usage_points"]} granted for {ret["user"]}'