from __future__ import unicode_literals
import logging
import unittest
import time
from xbahn.connection import connect, listen, link

#set up debug logging to console
logger = logging.getLogger("xbahn")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(logging.Formatter("%(name)s: %(message)s"))

logger.addHandler(ch)

# zmq socket types and path suffix required for their respective
# urls
ZMQ_TYPES = {
    "rep":"",
    "req":"",
    "pub":"/test",
    "sub":"/test",
    "push":"",
    "pull":""
}

# generate zmq urls for testing
URL_ZMQ = [
    dict(
        [
            (typ.upper(), "zmq://addr1/%s%s?transport=inproc" % (typ, path))
            for typ, path in list(ZMQ_TYPES.items())
        ]
    ),
    dict(
        [
            (typ.upper(), "zmq://addr2/%s%s?transport=inproc" % (typ, path))
            for typ, path in list(ZMQ_TYPES.items())
        ]
    )
]


class XbahnTestCase(unittest.TestCase):

    def setUpConnections(self, listeners, connections, tmpl=URL_ZMQ):
        self.listeners = []
        self.connections = []

        for typ, n in listeners:
            self.listeners.append(listen(tmpl[n][typ]))
        for typ, n in connections:
            self.connections.append(connect(tmpl[n][typ]))

    def tearDownConnections(self):
        for connection in self.connections:
            connection.destroy()
        for listener in self.listeners:
            listener.destroy()


    def tearDown(self):
        self.tearDownConnections()
        #time.sleep(1)
