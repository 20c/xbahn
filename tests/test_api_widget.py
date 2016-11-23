from builtins import object
import sys
import unittest
import asyncore
import time
import uuid
import pytest

import xbahn.connection.zmq
import xbahn.connection.link as link
import xbahn.api as api
import xbahn.message as message
import xbahn.exceptions as exceptions
import threading

from conftest import XbahnTestCase

class Server(api.WidgetAwareServer):
    pass

class UnawareServer(api.Server):
    class widget(api.Server.widget):
        widgets = {}

class Client(api.Client):
    pass

@Server.widget('test')
class ServerWidget(api.Widget):

    value = None

    @api.expose
    def hello(self):
        return "world"

    @api.expose
    def server_route(self):
        return self.comm.path

    @api.expose
    def set_value(self, v):
        self.value = v

    @api.expose
    def get_value(self):
        return self.value

@UnawareServer.widget('test')
class UnawareServerWidget(ServerWidget):
    pass

@Client.widget('test')
class ClientWidget(api.Widget):

    number = 0

    @api.expose
    def ping(self):
        return "pong"

    @api.expose
    def client_route(self):
        return self.comm.path

    @api.expose
    def set_number(self, n):
        self.number = n



@Client.widget('test2', remote_name='test')
class ClientWidgetB(api.Widget):
    pass


class Base(object):

    class TestAPIWidget(XbahnTestCase):

        def setUp(self):
            pass

        def test_widget_registry(self):
            self.assertEqual(Server.widget.widgets["test"], ServerWidget)
            self.assertEqual(Client.widget.widgets["test"], ClientWidget)
            self.assertEqual(Client.widget.widgets["test2"], ClientWidgetB)

            self.assertEqual(ClientWidgetB.remote_name, "test")


        def _test_unaware_comm(self, server, client):
            """
            Test widget communicating with widget unware server.
            """

            widget = ClientWidget(client, "test_widget")
            self.assertEqual(widget.hello(), "world")

            widget.set_value(1)
            self.assertEqual(widget.get_value(), 1)

            widget_b = ClientWidget(client, "test_widget")
            self.assertEqual(widget_b.get_value(), 1)



        def _test_comm(self, server, client):
            # instantiate client side widget
            widget = ClientWidget(client, "test_widget")

            # widget aware server should have created an instance of it's own
            self.assertEqual(isinstance(server.widgets["test"][widget.id], ServerWidget), True)

            self.assertEqual(widget.path, "widgets.%s.%s" % (ClientWidget.name, widget.id))
            self.assertEqual(widget.path, server.widgets["test"][widget.id].path)

            # instnatiate another client side widget
            widget_b = ClientWidgetB(client, "test_widget_b")
            widget_b.hello()

            # widget aware server should have created an instance of it's own (using remote_name
            # to identify the widget class)
            self.assertEqual(isinstance(server.widgets["test"][widget_b.id], ServerWidget), True)

            # client widget calling server widget method
            self.assertEqual(widget.hello(), "world")

            # server widget calling client widget method
            self.assertEqual(server.widgets["test"][widget.id].ping(), "pong")

            # ping doesnt exist on the second client
            with self.assertRaises(exceptions.APIError) as inst:
                server.widgets["test"][widget_b.id].ping()

            # another instance of widget b 
            widget_b2 = ClientWidgetB(client, "test_widget_b")

            widget.set_value("A")
            widget_b.set_value("B")

            self.assertEqual(widget.get_value(), "A")
            self.assertEqual(widget_b.get_value(), "B")
            self.assertEqual(widget_b2.get_value(), "B")

        def _test_widget_timeout(self, server, client):
            widget = ClientWidget(client, "test_widget")
            self.assertEqual(isinstance(server.widgets["test"][widget.id], ServerWidget), True)

            time.sleep(1)
            self.assertIn(widget.id, server.widgets["test"])
            time.sleep(1.5)
            self.assertNotIn(widget.id, server.widgets["test"])

            widget.hello()
            #server.clients[client.id].request_widget(widget.name, widget.id)
            self.assertIn(widget.id, server.widgets["test"])



        def _test_widget_routes(self, server_a, server_b, client_a, client_b):

            widget_a = ClientWidget(client_a, "test_widget")
            widget_b = ClientWidget(client_b, "test_widget")

            self.assertEqual(widget_a.server_route(), "route_a")
            self.assertEqual(widget_b.server_route(), "route_b")

            server_a.widgets["test"][widget_a.id].set_number(10)
            server_b.widgets["test"][widget_b.id].set_number(20)

            self.assertEqual(widget_a.number, 10)
            self.assertEqual(widget_b.number, 20)


        def _test_widget_groups(self, server, client):

            widget_a = ClientWidget(client, "widget_a", group="a")
            widget_b = ClientWidget(client, "widget_b", group="a")
            widget_c = ClientWidget(client, "widget_c")

            group = client.widgets["test"].filter(group="a")

            self.assertEqual(len(group), 2)
            self.assertIn(widget_a.id, group)
            self.assertIn(widget_b.id, group)
            self.assertNotIn(widget_c.id, group)

            group.set_value("testing")

            self.assertEqual(server.widgets["test"][widget_a.id].value, "testing")
            self.assertEqual(server.widgets["test"][widget_b.id].value, "testing")
            self.assertEqual(server.widgets["test"][widget_c.id].value, None)

            group = server.widgets["test"].filter(group="a")

            self.assertEqual(len(group), 2)
            self.assertIn(widget_a.id, group)
            self.assertIn(widget_b.id, group)
            self.assertNotIn(widget_c.id, group)

            group.set_number(10)

            self.assertEqual(widget_a.number, 10)
            self.assertEqual(widget_b.number, 10)
            self.assertEqual(widget_c.number, 0)




class TestAPIWidgetZMQ(Base.TestAPIWidget):

    def setUp(self):
        self.setUpConnections(
            [("REP",0),("REP",1)],
            [("REQ",0),("REQ",0)]
        )

    @pytest.mark.timeout(2)
    def test_unaware_comm_reqrep(self):
        link_server = link.Link()
        link_server.wire(
            "main",
            receive=self.listeners[0],
            respond=self.listeners[0]
        )

        link_client = link.Link()
        link_client.wire(
            "main",
            receive=self.connections[0],
            send=self.connections[0]
        )

        server = UnawareServer(link=link_server)
        client = Client(link=link_client)
        self._test_unaware_comm(server, client)

    @pytest.mark.timeout(2)
    def test_comm_reqrep(self):
        link_server = link.Link()
        link_server.wire(
            "main",
            receive=self.listeners[0],
            respond=self.listeners[0]
        )

        link_client = link.Link()
        link_client.wire(
            "main",
            receive=self.connections[0],
            send=self.connections[0],
            meta={"remote":self.listeners[1].remote}
        )
        link_client.wire(
            "responder",
            receive=self.listeners[1],
            respond=self.listeners[1]
        )

        server = Server(link=link_server)
        client = Client(link=link_client)
        self._test_comm(server, client)

    @pytest.mark.timeout(4)
    def test_widget_timeout(self):
        link_server = link.Link()
        link_server.wire(
            "main",
            receive=self.listeners[0],
            respond=self.listeners[0]
        )

        link_client = link.Link()
        link_client.wire(
            "main",
            receive=self.connections[0],
            send=self.connections[0],
            meta={"remote":self.listeners[1].remote}
        )
        link_client.wire(
            "responder",
            receive=self.listeners[1],
            respond=self.listeners[1]
        )

        server = Server(link=link_server, inactive_timeout=1.5)
        client = Client(link=link_client)
        self._test_widget_timeout(server, client)



    @pytest.mark.timeout(2)
    def test_widget_groups(self):
        link_server = link.Link()
        link_server.wire(
            "main",
            receive=self.listeners[0],
            respond=self.listeners[0]
        )

        link_client = link.Link()
        link_client.wire(
            "main",
            receive=self.connections[0],
            send=self.connections[0],
            meta={"remote":self.listeners[1].remote}
        )
        link_client.wire(
            "responder",
            receive=self.listeners[1],
            respond=self.listeners[1]
        )

        server = Server(link=link_server)
        client = Client(link=link_client)
        self._test_widget_groups(server, client)


    @pytest.mark.timeout(2)
    def test_widget_routes(self):
        link_server = link.Link()
        link_server.wire(
            "main",
            receive=self.listeners[0],
            respond=self.listeners[0]
        )

        link_client = link.Link()
        link_client.wire(
            "main",
            receive=self.connections[0],
            send=self.connections[0],
            meta={"remote":self.listeners[1].remote}
        )
        link_client.wire(
            "responder",
            receive=self.listeners[1],
            respond=self.listeners[1]
        )

        server_a = Server(link=link_server, path="route_a")
        server_b = Server(link=link_server, path="route_b")
        client_a = Client(link=link_client, path="route_a")
        client_b = Client(link=link_client, path="route_b")
        self._test_widget_routes(server_a, server_b, client_a, client_b)

