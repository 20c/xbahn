from builtins import object
import sys
import unittest
import pytest
import time
import uuid

import xbahn.connection.zmq
import xbahn.connection.link as link
import xbahn.api as api
import xbahn.message as message
import xbahn.exceptions as exceptions
import threading

from conftest import XbahnTestCase

class Server(api.ClientAwareServer):
    @api.expose
    def hello(self):
        return "hello"

class Client(api.Client):
    @api.expose
    def test(self):
        return "%s reporting" % self.id

class Base(object):

    class TestAPI2Way(XbahnTestCase):

        def setUp(self):

            # set up the server link, which will be able to
            # receive requests from the client and respond
            # to them
            self.link_server = link.Link()
            self.link_server.wire(
                "main",
                receive = self.listeners[0],
                respond = self.listeners[0]
            )

            # set up the client link
            self.link_client = link.Link()

            # first client link wire allows it to send requests
            # to the server and receive server responses
            self.link_client.wire(
                "main",
                receive = self.connections[0],
                send = self.connections[0],

                # we will send a meta variable called "remote"
                # with every message that will let the server know
                # how initiated two-way communication
                meta = {"remote":self.listeners[1].remote}
            )

            # second client link wire allows it to receive
            # requests from the server and respond to them
            self.link_client.wire(
                "responder",
                receive = self.listeners[1],
                respond = self.listeners[1]
            )


        @pytest.mark.timeout(2)
        def test_dispatch(self):
            server = Server(link=self.link_server)
            client_a = Client(link=self.link_client)

            self.assertEqual(client_a.hello(), "hello")
            self.assertIn(client_a.id, server.clients)
            self.assertEqual(server[client_a.id].test(), "%s reporting" % client_a.id)

        @pytest.mark.timeout(5)
        def test_inactivity_timeout(self):
            """
            Tests that clients that havent been active will be closed and
            removed
            """

            server = Server(link=self.link_server, inactive_timeout=2)
            client_a = Client(link=self.link_client)

            self.assertEqual(client_a.hello(), "hello")
            time.sleep(1)
            self.assertIn(client_a.id, server.clients)
            time.sleep(2.5)
            self.assertNotIn(client_a.id, server.clients)





class TestAPI2WayZMQ(Base.TestAPI2Way):

    def setUp(self):
        self.setUpConnections(
            [("REP",0),("REP",1)],
            [("REQ",0)]
        )
        super(TestAPI2WayZMQ, self).setUp()
