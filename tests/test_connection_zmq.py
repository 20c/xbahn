import pytest
import unittest
import xbahn.connection.zmq
import time

from xbahn.connection import connect, listen, link
from xbahn.message import Message

from conftest import URL_ZMQ, XbahnTestCase

class TestCasePUSHPULL(XbahnTestCase):

    """
    Tests PUSH / PULL connection
    """

    def setUp(self):
        self.setUpConnections(
            [("PUSH",0)],
            [("PULL",0), ("PULL",0)]
        )

    @pytest.mark.timeout(2)
    def test_push_pull(self):

        tester = self
        status = {}

        def handle_receive_connection(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            self.assertIn(message.data, ["first","second"])
            status[message.data] = True

        for conn in self.connections:
            conn.on("receive", handle_receive_connection, once=True)

        self.listeners[0].send(Message("first"))
        self.listeners[0].send(Message("second"))

        while "first" not in status or "second" not in status:
            time.sleep(0.01)



class TestCasePUBSUB(XbahnTestCase):

    """
    Tests PUB / SUB connection
    """

    def setUp(self):
        self.setUpConnections(
            [("PUB",0)],
            [("SUB",0), ("SUB",0)]
        )

    @pytest.mark.timeout(2)
    def test_pub_sub(self):

        """
        Tests a pub / sub exchange
        """

        tester = self
        counter = []

        def handle_receive_connection(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            tester.assertEqual(message.data, "Ping!")
            counter.append(event_origin)

        for conn in self.connections:
            conn.on("receive", handle_receive_connection, once=True)

        self.listeners[0].send(Message("Ping!"))

        while len(counter) < len(self.connections):
            time.sleep(0.01)



class TestCaseREQREP(XbahnTestCase):

    """
    Tests REQ / REP connection
    """

    def setUp(self):
        self.setUpConnections(
            [("REP",0)],
            [("REQ",0)]
        )


    @pytest.mark.timeout(2)
    def test_rep_req(self):

        """
        Tests a rep / req exchange with a manually manufactored
        response
        """

        tester = self
        counter = []

        def handle_receive_listener(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            self.assertEqual(message.data, "Hello")
            event_origin.respond(message, Message("World"))
            counter.append(event_origin)

        def handle_receive_connection(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            self.assertEqual(message.data, "World")
            counter.append(event_origin)


        self.listeners[0].on("receive", handle_receive_listener, once=True)
        self.connections[0].on("receive", handle_receive_connection, once=True)

        self.connections[0].send(Message("Hello"))

        while len(counter) != 2:
            time.sleep(0.01)

    @pytest.mark.timeout(2)
    def test_rep_req_auto_response(self):

        """
        Tests a rep / req exchange with an automatically manufactured
        null response from the rep connection
        """

        tester = self
        counter = []

        def handle_receive_listener(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            self.assertEqual(message.data, "Hello")
            counter.append(event_origin)

        def handle_receive_connection(**kwargs):
            message = kwargs.get("message")
            event_origin = kwargs.get("event_origin")
            self.assertEqual(message.data, None)
            counter.append(event_origin)


        self.listeners[0].on("receive", handle_receive_listener, once=True)
        self.connections[0].on("receive", handle_receive_connection, once=True)
        self.connections[0].send(Message("Hello"))

        while len(counter) != 2:
            time.sleep(0.01)

