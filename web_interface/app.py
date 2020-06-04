#!/usr/bin/env python3

import os
import threading
import time
import asyncio

from aiohttp import web
from jinja2 import Environment, PackageLoader, select_autoescape

from dataconnect import DataConnect, DataConnectError
import config

MY_DIR = os.path.dirname(os.path.realpath(__file__))

jinga = Environment(
    loader=PackageLoader('web_interface', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

data_connect_proxy = None

def handle_authorize_redirect(request):

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

def handle_root(request):
    template = jinga.get_template('layout.html')
    html = template.render(the='variables', go='here')
    return web.Response(body=html, content_type='text/html')

app = web.Application()
app.add_routes([web.get('/redirect', handle_authorize_redirect)])
app.add_routes([web.get('/', handle_root)])

# TODO use a reverse proxy
app.add_routes([web.static('/assets', os.path.join(MY_DIR, "assets"))])

async def start(run=False):

    runner = web.AppRunner(app)

    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port=3000)
    await site.start()

    while run:
        await asyncio.sleep(1)

if __name__ == '__main__':

    # Web interface can launched alone with
    # python -m web_interface.app

    import logging

    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(start(run=True))
    except KeyboardInterrupt:
        pass