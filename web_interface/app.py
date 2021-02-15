#!/usr/bin/env python3

import os
import threading
import logging
import time
import asyncio
from urllib.parse import urlencode

from aiohttp import web
from jinja2 import Environment, PackageLoader, select_autoescape

from dataconnect import DataConnect, DataConnectError, TEST_CLIENTS
import config

MY_DIR = os.path.dirname(os.path.realpath(__file__))

jinga = Environment(
    loader=PackageLoader('web_interface', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

data_connect_proxy = None

def handle_authorize_redirect(request):

    state = request.query.get('state', None)

    if state is None:
        # There is no state information,
        # we cannot link this redirect to a particular request
        code = request.query.get('code', None)
        error = request.query.get('error', None)
        error_description = request.query.get('error_description', None)
        # https://…/redirect?code=403&error=access_denied&error_description=authorization_request_refused
        if code == '403':
            return redirect_error(message='Vous n’avez pas autorisé Enedis à nous transmettre vos données.')
        else:
            # https://…/redirect?code=500&error=server_error&error_description=lincs-internal-server-error
            message = f'{error} ({code}): {error_description}'
            logging.error(f'Redirect Error: {message}')
            return redirect_error(message=f'Erreur Enedis: {message}', go_back=True)

    # Temporarily use the proxy for other web apps and tests
    # FIXME(cyril) Remove / Define in config file  
    if 'bmhs' in state:
        if 'local' in state:
            redirect_uri = 'http://localhost:8080/smarthome-application/'
        else:
            redirect_uri = 'https://dc.breizh-sen2.eu/'
        raise web.HTTPFound(redirect_uri + 'dataConnect/redirect?' + urlencode(request.query))

    code = request.query.get('code', None)

    if code is None:
        logging.error(f'Redirect Error: code parameter is missing')
        return redirect_error(message='Code parameter is missing', go_back=True)

    try:
        ret = data_connect_proxy.authorize_request_callback(code, state)
    except DataConnectError as e:
        logging.error(f'Redirect Error: {e}')
        raise web.HTTPInternalServerError(text=str(e))

    if ret is None:
        message = f"state {state} is not known"
        logging.error(f'Redirect Error: {message}')
        raise web.HTTPNotFound(message)

    redirect_uri = ret.get('redirect_uri')
    if redirect_uri:
        usage_points = ",".join(ret["usage_points"])
        # TODO proper query parameter appending and escpaping
        if '?' in redirect_uri:
            redirect_uri = redirect_uri + '&usage_points=' + usage_points
        else:
            redirect_uri = redirect_uri + '?usage_points=' + usage_points
        # TODO check code to prevent caching
        # (maybe that was the cause of the bug in the enedis portal)
        raise web.HTTPFound(redirect_uri)
    else:
        template = jinga.get_template('redirect_ok.html')
        html = template.render(usage_points=ret["usage_points"])
        return web.Response(body=html, content_type='text/html')

def redirect_error(message, go_back=False):
    template = jinga.get_template('redirect_error.html')
    html = template.render(message=message, go_back=go_back)
    return web.Response(body=html, content_type='text/html')

def handle_root(request):
    template = jinga.get_template('layout.html')
    html = template.render(the='variables', go='here')
    return web.Response(body=html, content_type='text/html')

def handle_authorize_description(request):
    template = jinga.get_template('authorize.html')
    if 'id' in request.query:
        uid = request.query['id']
    else:
        raise web.HTTPInternalServerError(text=f"'id' parameter is required")

    description = data_connect_proxy.authorize_descriptions.get(uid)
    if description is None:
        raise web.HTTPNotFound(text=f"id {uid} not found")

    redirect_uri = request.query.get('redirect_uri')
    duration = request.query.get('duration', 'P1Y')
    user_state = None

    test_client_id = request.query.get('test_client', None)

    if test_client_id is None:
        test_client_description = None
    elif not test_client_id in TEST_CLIENTS:
        test_client_id = None
        test_client_description = "test_client invalide"
    else:
        desc = TEST_CLIENTS[test_client_id]
        test_client_description = f"Utilisation du bac à sable avec le profile client {test_client_id}: {desc}"

    authorize_uri = data_connect_proxy.register_authorize_request(redirect_uri, duration, description['jid'], user_state, test_client_id)

    html = template.render(description=description, authorize_uri=authorize_uri, test_client_description=test_client_description)
    return web.Response(body=html, content_type='text/html')

app = web.Application()
app.add_routes([web.get('/redirect', handle_authorize_redirect)])
app.add_routes([web.get('/authorize', handle_authorize_description)])
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
