#!/usr/bin/env python3

import logging
import asyncio
import datetime as dt

from slixmpp import ClientXMPP
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin

import config
from dataconnect import DataConnect, DataConnectError
import json

class XmppInterface(ClientXMPP):

    def __init__(self, jid, password, make_authorize_uri, get_consumption_load_curve):
        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)

        self.register_plugin('xep_0004')
        self.register_plugin('xep_0050')
        self.register_plugin('xep_0199', {'keepalive': True, 'frequency':15})

        self.authorize_uri_handler = AuthorizeUriCommandHandler(self, make_authorize_uri)
        self.consumption_load_curve_handler = ConsumptionLoadCurveCommandHandler(self, get_consumption_load_curve)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # are sent asynchronously. You can almost always provide a
        # callback that will be executed when the reply is received.

        # We add the command after session_start has fired
        # to ensure that the correct full JID is used.

        # If using a component, may also pass jid keyword parameter.

        # TODO only list commands available to a particular user
        # TODO respond 403 when not authorized
        self['xep_0050'].add_command(node='get_authorize_uri',
                                     name='Request authorize URI',
                                     handler=self.authorize_uri_handler.handle_request)

        self['xep_0050'].add_command(node='get_consumption_load_curve',
                                     name='Get consumption load curve',
                                     handler=self.consumption_load_curve_handler.handle_request)

    def notify_authorize_complete(self, dest, usage_points, state):

        msg = self.make_message(mto=dest, mtype="chat")

        body = ET.Element('body')
        body.text = f'Access granted for usage points {", ".join(usage_points)}'

        x = ET.Element('x', xmlns="https://consometers.org/dataconnect#authorize")

        for usage_point in usage_points:
            usage_point_element = ET.Element('usage-point')
            usage_point_element.text = usage_point
            x.append(usage_point_element)

        state_element = ET.Element('state')
        state_element.text = state
        x.append(state_element)

        msg.append(body)
        msg.append(x)
        msg.send()

    def message(self, msg):
        if not msg['type'] in ('chat', 'normal'):
            print(msg)
            return

        # Trying to send a form to a user, without using ad-hoc commands
        # Only worked with Psi

        dst_jid = msg['from']

        form = self["xep_0004"].make_form(title="hello", ftype="form")
        form.set_instructions('Please fill in the following form')
        form.add_field(var='field-1', label='Text Input', ftype="text-single")

        msg = xmpp.make_message(mto=dst_jid, mfrom=xmpp.boundjid.full)
        msg.append(form)
        msg.send()

class AuthorizeUriCommandHandler:

    def __init__(self, xmpp_client, make_authorize_uri):

        self.xmpp = xmpp_client
        self.make_authorize_uri = make_authorize_uri

    def handle_request(self, iq, session):

        if iq['command']['action'] == "complete":
            return self.handle_submit(session['payload'], session)

        form = self.xmpp['xep_0004'].make_form(ftype='form', title='Request authorize URI')

        # form['instructions'] = 'Request authorize URI'

        # session['notes'] = [             -- Add informative notes about the
        #   ('info', 'Info message'),         command's results.
        #   ('warning', 'Warning message'),
        #   ('error', 'Error message')]

        form.addField(var='redirect_uri',
                      ftype='text-single',
                      label='Redirect URI',
                      desc='Adresse de redirection après consentement',
                      value='')

        form.addField(var='duration',
                      ftype='text-single',
                      label='Duration',
                      desc=' Au format ISO 8601, ne peut excéder 3 ans.',
                      required=True,
                      value='P1Y')

        form.addField(var='state',
                      ftype='text-single',
                      label='State',
                      desc='Données permettant d’identifier le résultat',
                      value='')

        session['payload'] = form
        session['next'] = self.handle_submit

        return session

    def handle_submit(self, payload, session):

        redirect_uri = payload['values'].get('redirect_uri', None)
        duration = payload['values']['duration']
        state = payload['values'].get('state', None)

        authorize_uri = self.make_authorize_uri(redirect_uri, duration, session['from'].bare, state)

        # authorize_uri = self.data_connect_proxy.register_authorize_request(redirect_uri, duration, session['from'].bare, state)

        form = self.xmpp['xep_0004'].make_form(ftype='result', title="Authorize URI")

        # TODO using ftype='fixed' would be more appropriate
        # but Psi won’t allow copy pasting
        form.addField(var='authorize_uri',
                      ftype='text-single',
                      label='Adresse pour recueillir le consentement',
                      value=authorize_uri)

        session['payload'] = form
        session['next'] = None

        return session

class ConsumptionLoadCurveCommandHandler:

    def __init__(self, xmpp_client, get_consumption_load_curve):

        self.xmpp = xmpp_client
        self.get_consumption_load_curve = get_consumption_load_curve

    def handle_request(self, iq, session):

        if iq['command']['action'] == "complete":
            return self.handle_submit(session['payload'], session)

        form = self.xmpp['xep_0004'].make_form(ftype='form', title='Get consumption load curve data')

        form.addField(var='usage_point_id',
                      ftype='text-single',
                      label='Usage point',
                      required=True,
                      value='')

        start_date = DataConnect.date_to_isostring(dt.datetime.today() - dt.timedelta(days=1))
        end_date = DataConnect.date_to_isostring(dt.datetime.today())

        form.addField(var='start_date',
                      ftype='text-single',
                      label='Start date',
                      desc=' Au format YYYY-MM-DD',
                      required=True,
                      value=start_date)

        form.addField(var='end_date',
                      ftype='text-single',
                      label='End date',
                      desc=' Au format YYYY-MM-DD',
                      required=True,
                      value=end_date)

        session['payload'] = form
        session['next'] = self.handle_submit

        return session

    def handle_submit(self, payload, session):

        usage_point_id = payload['values']['usage_point_id']
        start_date = payload['values']['start_date']
        end_date = payload['values']['end_date']

        try:
            data = self.get_consumption_load_curve(session['from'].bare, usage_point_id, start_date, end_date)
        except DataConnectError as e:
            return self.fail_with(str(e), session)
        print(data)
        session['next'] = None

        xmldata = ET.Element('data', xmlns="urn:quoalise:sen2:load_curve")
        sensml = ET.Element('sensml', xmlns="urn:ietf:params:xml:ns:senml")

        meter_reading = data['usage_point'][0]["meter_reading"]
        date = meter_reading["start"]
        measurements = meter_reading["interval_reading"]
        first = True
        for measurement in measurements:
            v = str(measurement['value'])
            t = str(int(measurement['rank']) * 30 * 60)
            if first:
                bt = DataConnect.date(date)
                bt = str(bt.replace(tzinfo=dt.timezone.utc).timestamp())
                senml = ET.Element('senml', bn=f"urn:dev:prm:{usage_point_id}_consumption_load", bt=bt, t=t, v=v, u='W')
                first = False
            else:
                senml = ET.Element('senml', t=t, v=v, u='W')
            sensml.append(senml)

        xmldata.append(sensml)


        # TODO keep a way to get a message instead of embedding data in the iq response
        msg = self.xmpp.make_message(mto=session['from'].bare,
                                    msubject=f"Consumption load curve for {usage_point_id}")
        msg.append(xmldata)
        msg.send()

        session['payload'] = None # xmldata

        return session

    def fail_with(self, message, session):
        session['payload'] = None
        session['next'] = None
        session['notes'] = [('error', message)]
        return session
