from builtins import object
import unittest
import pytest
import time
import xbahn.connection.zmq
import xbahn.connection.link as link
from xbahn.message import Message

from conftest import XbahnTestCase

class Base(object):

    """
    We keep the base test case in here, so it doesn't
    get picked up by py.test
    """

    class LinkTestCase(XbahnTestCase):

        @pytest.mark.timeout(2)
        def test_link_wire_cut(self):
            """
            Test cutting and disconnecting wires
            """
            link_rep = link.Link()
            link_rep.wire(
                "main",
                receive=self.listeners[0]
            )
            link_rep.wire(
                "send_wire",
                send=self.connections[0]
            )

            link_rep.cut("main")
            self.assertEqual(getattr(link_rep, "main", None), link_rep.send_wire)
            link_rep.cut("send_wire")
            self.assertEqual(getattr(link_rep, "main", None), None)
            self.assertEqual(getattr(link_rep, "send_wire", None), None)

        @pytest.mark.timeout(2)
        def test_link_disconnect(self):
            """
            Test cutting and disconnecting wires
            """
            link_rep = link.Link()
            link_rep.wire(
                "main",
                receive=self.listeners[0]
            )
            link_rep.disconnect()

            self.assertEqual(link_rep.main, None)
            self.assertEqual(self.listeners[0].close_when_ready, True)



        @pytest.mark.timeout(2)
        def test_link_send_and_receive(self):

            """
            Test sending and receiving via links (one connection each)
            """

            link_rep = link.Link()
            link_rep.wire(
                "main",
                receive=self.listeners[0]
            )

            link_req = link.Link()
            link_req.wire(
                "main",
                send=self.connections[0]
            )

            self.assertEqual(isinstance(link_req.main, link.Wire), True)
            self.assertEqual(isinstance(link_rep.main, link.Wire), True)

            status = {}

            def rep_receive(**kwargs):
                message = kwargs.get("message")
                status[message.data] = True

            link_rep.on("receive", rep_receive, once=True)
            link_req.main.send("test", Message("Ping!"))

            while status.get("Ping!") != True:
                time.sleep(0.01)


        @pytest.mark.timeout(2)
        def test_link_receive_multiple(self):

            """
            Test receiving from multiple connections
            """

            link_rep = link.Link()
            link_rep.wire(
                "first",
                receive=self.listeners[0]
            )
            link_rep.wire(
                "second",
                receive=self.listeners[1]
            )

            link_req = link.Link()
            link_req.wire(
                "first",
                send=self.connections[0]
            )
            link_req.wire(
                "second",
                send=self.connections[1]
            )

            self.assertEqual(isinstance(link_req.first, link.Wire), True)
            self.assertEqual(isinstance(link_req.second, link.Wire), True)
            self.assertEqual(isinstance(link_rep.first, link.Wire), True)
            self.assertEqual(isinstance(link_rep.second, link.Wire), True)

            status = {}

            def rep_receive(**kwargs):
                message = kwargs.get("message")
                status[message.data] = True

            link_rep.on("receive", rep_receive)
            link_req.first.send("test", Message("First!"))
            link_req.second.send("test", Message("Second!"))

            while status.get("First!") != True or status.get("Second!") != True:
                time.sleep(0.01)



        @pytest.mark.timeout(2)
        def test_link_send_receive_respond(self):

            """
            Tests responding to a received message
            """

            link_rep = link.Link()
            link_rep.wire(
                "main",
                receive=self.listeners[0],
                respond=self.listeners[0]
            )

            link_req = link.Link()
            link_req.wire(
                "main",
                receive=self.connections[0],
                send=self.connections[0]
            )

            self.assertEqual(isinstance(link_req.main, link.Wire), True)
            self.assertEqual(isinstance(link_rep.main, link.Wire), True)

            status = {}

            def rep_receive_ping(**kwargs):
                message = kwargs.get("message")
                wire = kwargs.get("wire")
                wire.respond(message, Message("Pong!"))
                status[message.data] = True

            def msg_response(message, **kwargs):
                status[message.data] = True

            ping_message = Message("Ping!")
            ping_message.on("response", msg_response)

            link_rep.on("receive_ping", rep_receive_ping, once=True)
            link_req.main.send("ping", ping_message)

            while status.get("Ping!") != True or status.get("Pong!") != True:
                time.sleep(0.01)





class TestLinkZMQ(Base.LinkTestCase):

    def setUp(self):
        self.setUpConnections(
            [("REP",0),("REP",1)],
            [("REQ",0),("REQ",1)]
        )

