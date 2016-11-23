from builtins import str
from builtins import object
import sys
import unittest
import asyncore
import time
import pytest

import xbahn.connection.zmq
import xbahn.connection.link as link
import xbahn.api as api
import xbahn.message as message
import xbahn.exceptions as exceptions
import threading

from conftest import XbahnTestCase

class Server(api.Server):

    @api.expose
    def action_a(self):
        return "a"

    @api.expose
    def action_b(self, arg):
        return "b:%s" % arg

    @api.expose
    def action_c(self, arg, extra=None):
        return "c (%s) extra=%s" % (arg, extra)

    @api.expose
    def action_d(self):
        return message.Message("d")

    @api.expose
    def action_error(self):
        raise Exception("Abandon ship!")

    @api.expose
    def my_route(self):
        return self.path

    def action_forbidden(self):
        return "not allowed"

class Base(object):

    """
    Keep the base test case in here so pytest does not
    pick it up
    """

    class APITestCase(XbahnTestCase):

        def setUp(self):
            self.server_link = link.Link()
            self.server_link.wire(
                "main",
                receive=self.listeners[0],
                respond=self.listeners[0]
            )
            self.client_link = link.Link()
            self.client_link.wire(
                "main",
                receive=self.connections[0],
                send=self.connections[0]
            )

        @pytest.mark.timeout(2)
        def test_dispatch(self):
            """
            tests dispatching function call from api client to api server
            """

            server = Server(link=self.server_link)
            client = api.Client(link=self.client_link)

            self.assertEqual(client.action_a(), "a")
            self.assertEqual(client.action_b("test"), "b:test")
            self.assertEqual(client.action_c("test",extra="more"), "c (test) extra=more")
            self.assertEqual(client.action_d(), "d")

            with self.assertRaises(exceptions.APIError) as inst:
                client.action_forbidden()

            with self.assertRaises(exceptions.APIError) as inst:
                client.action_error()
                self.assertEqual(str(inst), "Abandon ship!")

        @pytest.mark.timeout(2)
        def test_dispatch_routing(self):

            """
            tests xbahn routing in api
            """

            server_a = Server(link=self.server_link, path="route_a")
            server_b = Server(link=self.server_link, path="route_b")

            client_a = api.Client(link=self.client_link, path="route_a")
            client_b = api.Client(link=self.client_link, path="route_b")

            self.assertEqual(client_a.my_route(), client_a.path)
            self.assertEqual(client_b.my_route(), client_b.path)

        @pytest.mark.timeout(2)
        def test_auth_handler(self):
            server = Server(link=self.server_link, handlers=[api.AuthHandler("secretkey")])
            client_a = api.Client(link=self.client_link, handlers=[api.AuthHandler("secretkey")])

            self.assertEqual(client_a.action_a(), "a")

            with self.assertRaises(exceptions.APIError) as inst:
                client_b = api.Client(link=self.client_link)
                self.assertEqual(str(inst), "Athentication failed.")


class TestAPIZMQ(Base.APITestCase):

    def setUp(self):
        self.setUpConnections(
            [("REP",0)],
            [("REQ",0)]
        )
        super(TestAPIZMQ, self).setUp()


