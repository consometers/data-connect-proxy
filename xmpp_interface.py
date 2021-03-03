#!/usr/bin/env python3

import logging
import asyncio
import datetime as dt
import pytz

from slixmpp import ClientXMPP
from slixmpp.exceptions import XMPPError
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin

import config
from dataconnect import DataConnect, DataConnectError
import json

def fail_with(message, code):

    args = {'issuer': 'enedis-data-connect'} # TODO directly use a xml ns?
    if code is not None:
        args['code'] = code

    raise XMPPError(extension="upstream-error",
                    extension_ns="urn:quoalise:0",
                    extension_args=args,
                    text=message,
                    etype="cancel")

class XmppInterface(ClientXMPP):

    def __init__(self, jid, password, make_authorize_uri, get_load_curve, get_daily):
        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)

        self.register_plugin('xep_0004')
        self.register_plugin('xep_0050')
        self.register_plugin('xep_0199', {'keepalive': True, 'frequency':15})

        self.authorize_uri_handler = AuthorizeUriCommandHandler(self, make_authorize_uri)
        self.load_curve_handler = LoadCurveCommandHandler(self, get_load_curve)
        self.daily_handler = DailyCommandHandler(self, get_daily)

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

        # TODO deprecated, replaced with get_load_curve
        self['xep_0050'].add_command(node='get_consumption_load_curve',
                                     name='Get consumption load curve',
                                     handler=self.load_curve_handler.handle_request)

        self['xep_0050'].add_command(node='get_load_curve',
                                     name='Get load curve',
                                     handler=self.load_curve_handler.handle_request)

        self['xep_0050'].add_command(node='get_daily',
                                     name='Get daily data',
                                     handler=self.daily_handler.handle_request)

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

        if iq['command'].xml: # has subelements
            return self.handle_submit(session['payload'], session)

        form = self.xmpp['xep_0004'].make_form(ftype='form', title='Request authorize URI')

        # form['instructions'] = 'Request authorize URI'

        # session['notes'] = [             -- Add informative notes about the
        #   ('info', 'Info message'),         command's results.
        #   ('warning', 'Warning message'),
        #   ('error', 'Error message')]

        form.addField(var='name',
                      ftype='text-single',
                      label='Nom du service',
                      value="Elec Expert Demo")

        # TODO add a value field for each line, see XEP-0004
        form.addField(var='service',
                      ftype='text-multi',
                      label='Description du service',
                      value='Nos experts analysent votre consommation d’électricité sur l’année précédente mesurée par votre compteur Linky.\n'+
                            'Lors d’un rendez-vous téléphonique, nous vous ferons part de nos recommandations pour mieux maîtriser votre consommation.')

        form.addField(var='processings',
                      ftype='text-multi',
                      label='Processings',
                      value='Analyse votre consommation d’électricité\nAffichage de graphiques')

        session['payload'] = form
        session['next'] = self.handle_submit

        return session

    def handle_submit(self, payload, session):

        name = payload['values'].get('name', session['from'].bare)
        service = payload['values'].get('service', None)
        processings = payload['values'].get('processings', None)

        authorize_uri = self.make_authorize_uri(session['from'].bare, name, service, processings)

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

class LoadCurveCommandHandler:

    def __init__(self, xmpp_client, get_load_curve):

        self.xmpp = xmpp_client
        self.get_load_curve = get_load_curve

    def handle_request(self, iq, session):

        if iq['command'].xml: # has subelements
            return self.handle_submit(session['payload'], session)

        form = self.xmpp['xep_0004'].make_form(ftype='form', title=f'Get load curve data')

        form.addField(var='usage_point_id',
                      ftype='text-single',
                      label='Usage point',
                      required=True,
                      value='')

        form.addField(var='direction',
                      ftype='list-single',
                      label='Direction',
                      options=[{'label': 'Consumption', 'value': 'consumption'},
                               {'label': 'Production', 'value': 'production'}],
                      required=True,
                      value='consumption')

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

        if 'direction' in payload['values']:
            direction = payload['values']['direction']
        else:
            direction = 'consumption'

        try:
            data = self.get_load_curve(direction, session['from'].bare, usage_point_id, start_date, end_date)
        except DataConnectError as e:
            # TODO does session needs cleanup?
            return fail_with(e.message, e.code)
        # print(data)

        form = self.xmpp['xep_0004'].make_form(ftype='result', title=f"Get {direction} load curve data")

        # TODO can't get reports to show properly on gajim
        # form.add_reported('result', ftype='fixed', label=f'Consumption load curve for {usage_point_id}')
        # form.add_item({'result': 'Success'})
        # TODO Psi won’t show session['notes'] = [('info', "…")]

        form.addField(var='result',
                      ftype='fixed',
                      label=f'{direction} load curve for {usage_point_id}',
                      value=f"Success")

        session['next'] = None

        # <quoalise xmlns="urn:quoalise:0">
        #   <!-- On peut éventuellement mettre plusieurs élements data -->
        #   <data>
        #     <meta>
        #       <!-- Les meta données utilisables pour tout type de données, à determiner -->
        #       <device type="electricity-meter">
        #         <identifier authority="enedis" type="prm" value="22516914714270"/>
        #       </device>
        #       <app id="https://datahub-enedis.fr/data-connect/">
        #         <!-- Les meta données propres à cette application ajoutées sous forme d’extension -->
        #         <data-connect xmlns="urn:consometers:dataconnect:0">
        #           <start>2020-06-01</start>
        #           <end>2020-06-02</end>
        #         </data-connect>
        #       </app>
        #       <measurement>
        #         <physical quantity="power" type="electrical" unit="W">
        #         <business graph="load-profile" direction="consumption"/>
        #         <aggregate type="average" />
        #         <sampling interval="1800" />
        #       </measurement>
        #     </meta>
        #     <senml></senml>
        #   </data>
        # </quoalise>

        class Quoalise(ElementBase):
          name = 'quoalise'
          namespace = 'urn:quoalise:0'

        quoalise = Quoalise()

        xmldata = ET.Element('data')
        quoalise.xml.append(xmldata)

        meta = ET.Element('meta')
        xmldata.append(meta)

        device = ET.Element('device', attrib={'type': "electricity-meter"})
        meta.append(device)
        device.append(ET.Element('identifier', attrib={'authority': "enedis", 'type': "prm", 'value': usage_point_id}))

        measurement_meta = ET.Element('measurement')
        meta.append(measurement_meta)
        measurement_meta.append(ET.Element('physical', attrib={'quantity': "power", 'type': "electrical", 'unit': "W"}))
        measurement_meta.append(ET.Element('business', graph="load-profile", direction=direction))
        measurement_meta.append(ET.Element('aggregate', attrib={'type': "average"}))

        sensml = ET.Element('sensml', xmlns="urn:ietf:params:xml:ns:senml")
        xmldata.append(sensml)

        meter_reading = data["meter_reading"]
        bt = DataConnect.date(payload['values']['start_date'])
        bt = int(bt.astimezone(pytz.utc).timestamp())

        measurements = meter_reading["interval_reading"]
        first = True
        for measurement in measurements:
            v = str(measurement['value'])
            t = DataConnect.datetime(measurement["date"])
            t = int(t.astimezone(pytz.utc).timestamp())
            t = t - bt
            if first:
                senml = ET.Element('senml',
                                   bn=f"urn:dev:prm:{usage_point_id}_{direction}_load",
                                   bt=str(bt), t=str(t), v=str(v), bu='W')
                measurement_meta.append(ET.Element('sampling', interval=measurement['interval_length']))
                first = False
            else:
                senml = ET.Element('senml', t=str(t), v=str(v))
            sensml.append(senml)

        # TODO keep a way, like a checkbox to get a message instead of embedding data in the iq response
        # msg = self.xmpp.make_message(mto=session['from'].bare,
        #                             msubject=f"Consumption load curve for {usage_point_id}")
        # msg.append(quoalise)
        #msg.send()

        session['payload'] = [form, quoalise]

        return session

class DailyCommandHandler:

    def __init__(self, xmpp_client, get_daily):

        self.xmpp = xmpp_client
        self.get_daily = get_daily

    def handle_request(self, iq, session):

        if iq['command'].xml: # has subelements
            return self.handle_submit(session['payload'], session)

        form = self.xmpp['xep_0004'].make_form(ftype='form', title=f'Get daily data')

        form.addField(var='usage_point_id',
                      ftype='text-single',
                      label='Usage point',
                      required=True,
                      value='')

        form.addField(var='direction',
                      ftype='list-single',
                      label='Direction',
                      options=[{'label': 'Consumption', 'value': 'consumption'},
                               {'label': 'Production', 'value': 'production'}],
                      required=True,
                      value='consumption')

        start_date = DataConnect.date_to_isostring(dt.datetime.today() - dt.timedelta(days=30))
        end_date = DataConnect.date_to_isostring(dt.datetime.today() - dt.timedelta(days=15))

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
        direction = payload['values']['direction']

        try:
            data = self.get_daily(direction, session['from'].bare, usage_point_id, start_date, end_date)
        except DataConnectError as e:
            return fail_with(e.message, e.code)
        print(data)

        form = self.xmpp['xep_0004'].make_form(ftype='result', title=f"Get daily {direction}")

        # TODO can't get reports to show properly on gajim
        # form.add_reported('result', ftype='fixed', label=f'Consumption load curve for {usage_point_id}')
        # form.add_item({'result': 'Success'})
        # TODO Psi won’t show session['notes'] = [('info', "…")]

        form.addField(var='result',
                      ftype='fixed',
                      label=f'{direction} load curve for {usage_point_id}',
                      value=f"Success")

        session['next'] = None

        class Quoalise(ElementBase):
          name = 'quoalise'
          namespace = 'urn:quoalise:0'

        quoalise = Quoalise()

        xmldata = ET.Element('data')
        quoalise.xml.append(xmldata)

        meta = ET.Element('meta')
        xmldata.append(meta)

        device = ET.Element('device', attrib={'type': "electricity-meter"})
        meta.append(device)
        device.append(ET.Element('identifier', attrib={'authority': "enedis", 'type': "prm", 'value': usage_point_id}))

        measurement = ET.Element('measurement')
        meta.append(measurement)
        measurement.append(ET.Element('physical', attrib={'quantity': "energy", 'type': "electrical", 'unit': "Wh"}))
        measurement.append(ET.Element('business', direction=direction))
        measurement.append(ET.Element('aggregate', attrib={'type': "sum"}))
        measurement.append(ET.Element('sampling', interval="P1D"))

        sensml = ET.Element('sensml', xmlns="urn:ietf:params:xml:ns:senml")
        xmldata.append(sensml)

        meter_reading = data["meter_reading"]
        bt = DataConnect.date(payload['values']['start_date'])
        bt = int(bt.astimezone(pytz.utc).timestamp())
        measurements = meter_reading["interval_reading"]
        first = True
        for measurement in measurements:
            v = str(measurement['value'])
            t = DataConnect.date(measurement["date"])
            t = int(t.astimezone(pytz.utc).timestamp())
            t = t - bt
            if first:
                senml = ET.Element('senml',
                                   bn=f"urn:dev:prm:{usage_point_id}_daily_{direction}",
                                   bt=str(bt), t=str(t), v=str(v), bu='Wh')
                first = False
            else:
                senml = ET.Element('senml', t=str(t), v=str(v))
            sensml.append(senml)

        # TODO keep a way, like a checkbox to get a message instead of embedding data in the iq response
        # msg = self.xmpp.make_message(mto=session['from'].bare,
        #                             msubject=f"Consumption load curve for {usage_point_id}")
        # msg.append(quoalise)
        #msg.send()

        session['payload'] = [form, quoalise]

        return session
