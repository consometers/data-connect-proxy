#!/usr/bin/env python3

import logging

import asyncio

from slixmpp import ClientXMPP
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin

import config

class XmppInterface(ClientXMPP):

    def __init__(self, jid, password, data_connect_proxy):
        ClientXMPP.__init__(self, jid, password)

        self.data_connect_proxy = data_connect_proxy

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        # If you wanted more functionality, here's how to register plugins:
        # self.register_plugin('xep_0030') # Service Discovery
        # self.register_plugin('xep_0199') # XMPP Ping

        # Here's how to access plugins once you've registered them:
        # self['xep_0030'].add_feature('echo_demo')

        self.register_plugin('xep_0004')
        self.register_plugin('xep_0050')

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # are sent asynchronously. You can almost always provide a
        # callback that will be executed when the reply is received.

        # We add the command after session_start has fired
        # to ensure that the correct full JID is used.

        # If using a component, may also pass jid keyword parameter.

        self['xep_0050'].add_command(node='authorize',
                                     name='Request authorize URI',
                                     handler=self.handle_authorize_command)

    def handle_authorize_command(self, iq, session):
        """
        Respond to the initial request for a command.
        Arguments:
            iq      -- The iq stanza containing the command request.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        form = self['xep_0004'].make_form(ftype='form')
        form['instructions'] = 'Request authorize URI'
        form.addField(var='redirect_uri',
                      ftype='text-single',
                      label='Adresse de redirection après consentement',
                      value='')

        form.addField(var='duration',
                      ftype='text-single',
                      label='Durée de l’autorisation',
                      value='P1Y')

        form.addField(var='state',
                      ftype='text-single',
                      label='Données associées',
                      value='')

        session['payload'] = form
        session['next'] = self.handle_make_authorize_url
        session['has_next'] = True
        # session['allow_complete'] = False

        # Other useful session values:
        # session['to']                    -- The JID that received the
        #                                     command request.
        # session['from']                  -- The JID that sent the
        #                                     command request.
        # session['has_next'] = True       -- There are more steps to complete
        # session['allow_complete'] = True -- Allow user to finish immediately
        #                                     and possibly skip steps
        # session['cancel'] = handler      -- Assign a handler for if the user
        #                                     cancels the command.
        # session['notes'] = [             -- Add informative notes about the
        #   ('info', 'Info message'),         command's results.
        #   ('warning', 'Warning message'),
        #   ('error', 'Error message')]

        return session

    def handle_make_authorize_url(self, payload, session):

        """
        Process a command result from the user.
        Arguments:
            payload -- Either a single item, such as a form, or a list
                       of items or forms if more than one form was
                       provided to the user. The payload may be any
                       stanza, such as jabber:x:oob for out of band
                       data, or jabber:x:data for typical data forms.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """

        # In this case (as is typical), the payload is a form

        redirect_uri = payload['values']['redirect_uri']
        duration = payload['values']['duration']
        state = payload['values']['state']

        print(session['from'])
        print(type(session['from']))

        authorize_uri = self.data_connect_proxy.register_authorize_request(redirect_uri, duration, session['from'].bare, state)

        form = self['xep_0004'].make_form(ftype='submit')
        form['instructions'] = 'Request authorize URI'
        form.addField(var='authorize_uri',
                      ftype='text-single',
                      label='Adresse pour recueillir le consentement',
                      value=authorize_uri)

        session['payload'] = form

        session['next'] = self.handle_command_complete
        session['has_next'] = False
        session['allow_complete'] = True

        return session

    def handle_command_complete(self, payload, session):
        session['payload'] = None
        session['next'] = None
        return session

    def notify_authorize_complete(self, dest, usage_points):

        msg = self.make_message(mto=dest, mfrom=self.boundjid.full, mtype="chat")

        body = ET.Element('body')
        body.text = f'Access granted for usage points {", ".join(usage_points)}'

        x = ET.Element('x', xmlns="https://consometers.org/dataconnect#authorize")

        for usage_point in usage_points:
            x.append(ET.Element('usage-point', id=usage_point))

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

if __name__ == '__main__':
    # Ideally use optparse or argparse to get JID,
    # password, and log level.

    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    xmpp = XmppInterface(config.XMPP_JID, config.XMPP_PASSWORD)
    xmpp.connect()
    xmpp.process()