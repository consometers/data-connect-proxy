#!/usr/bin/env python3

import threading
import time
import asyncio
import logging

from aiohttp import web

from dataconnect import DataConnect, DataConnectError
import config

import ssl

data_connect_proxy = None

def authorize_redirect(request):

    if 'code' in request.query:
        code = request.query['code']
    else:
        raise web.HTTPInternalServerError(text=f"'code' parameter is required")

    if 'state' in request.query:
        state = request.query['state']
    else:
        state = None

    try:
        ret = data_connect_proxy.authorize_request_callback(code, state)
    except DataConnectError as e:
        raise web.HTTPInternalServerError(text=str(e))

    # TODO use exception instead
    if ret is None:
        return None

    if ret['redirect_uri']:
        # TODO check code to prevent caching
        # (maybe that was the cause of the bug in the enedis portal)
        raise web.HTTPFound(ret['redirect_uri'])
        # return redirect(ret['redirect_uri'], code=302)
    else:
        return web.Response(text=f'Access to usage points {ret["usage_points"]} granted for {ret["user"]}')

app = web.Application()
app.add_routes([web.get('/', authorize_redirect)])

async def start_app():

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')

    runner = web.AppRunner(app)

    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port=443, ssl_context=ssl_context)
    await site.start()