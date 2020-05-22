#!/usr/bin/env python3

import logging

import asyncio

from slixmpp import ClientXMPP

import config

class XmppInterface(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

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
                                     name='Authorize',
                                     handler=self._handle_command)

    def _handle_command(self, iq, session):
        """
        Respond to the initial request for a command.
        Arguments:
            iq      -- The iq stanza containing the command request.
            session -- A dictionary of data relevant to the command
                       session. Additional, custom data may be saved
                       here to persist across handler callbacks.
        """
        form = self['xep_0004'].make_form('form', 'Greeting')
        form['instructions'] = 'Send a custom greeting to a JID'
        form.addField(var='redirrect_uri',
                      ftype='text-single',
                      label='Adresse vers laquelle l‘utilisateur sera redirigé après avoir exprimé son consentement',
                      value='https://cyril.lu/dataconnect-proxy/redirect')

        form.addField(var='state',
                      ftype='text-single',
                      label='Sera ajouté en paramètre à l’adresse de redirection pour maintenir l’état entre la requête et la redirection',
                      value='')

        form.addField(var='state',
                      ftype='text-single',
                      label='Durée pendant laquelle l’application souhaite accéder aux données du client, au format ISO 8601, ne peut excéder 3 ans',
                      value='P1Y')

        session['payload'] = form
        session['next'] = self._handle_command_complete
        session['has_next'] = False

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

    def _handle_command_complete(self, payload, session):
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
        form = payload

        greeting = form['values']['greeting']

        self.send_message(mto=session['from'],
                          mbody="%s, World!" % greeting,
                          mtype='chat')

        # Having no return statement is the same as unsetting the 'payload'
        # and 'next' session values and returning the session.

        # Unless it is the final step, always return the session dictionary.

        session['payload'] = None
        session['next'] = None

        return session

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