from __future__ import print_function
import socket, asynchat, asyncore
import time

from xbahn.mixins import EventMixin

from xbahn.connection import (
    register,
    Poller as BasePoller,
    Receiver as BaseReceiver,
    Sender as BaseSender
)

maps = {}
pollers = {}

def make_map(host, port):
    key = (host, port)
    if key not in maps:
        maps[key] = {}
    return maps[key]

TERMINATOR = ":::XBAHN-MESSAGE"

class Poller(BasePoller):
    def __init__(self, host, port):
        super(Poller, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        asyncore.loop(map=make_map(self.host, self.port), timeout=0.5)
        try:
            del pollers[(self.host, self.port)]
        except KeyError:
            pass


class Handler(EventMixin, asynchat.async_chat):

    """
    This will be instantiated by the server when a connection
    is made. Since this is a direct connection responses
    will be sent through this object
    """

    # direct connection, responses are handled through
    # this, so we flag this as a responder
    responder = True

    def __init__(self, host, port, sock=None, temporary=False):
        EventMixin.__init__(self)
        asynchat.async_chat.__init__(self, sock, map=make_map(host, port))
        self.set_terminator(TERMINATOR)
        self.received_data = ""
        self.temporary = temporary
        self.sock = sock
        self.dispatcher = None
        self.time = 0

    def is_active(self, t, delay, close=True):
        if t - self.time > delay:
            print("closing", self, "because inactive", delay)
            if close:
                self.close_when_done()
            return False
        return True

    def collect_incoming_data(self, data):
        """
        Collect incoming data into self.received_data
        """

        self.received_data += data


    def found_terminator(self):

        """
        Terminator has been found, process data
        """

        self.process_data()

    def process_data(self):

        """
        Process data

        Triggers raw-data-received event
        """
        self.trigger("process-data", self.received_data)
        self.received_data = ""
        if self.dispatcher:
            self.time = self.dispatcher.time


    def respond(self, data):
        """
        Respond to the connection accepted in this object
        """

        self.push("%s%s" % (data, TERMINATOR))
        if self.temporary:
            self.close_when_done()


class Receiver(BaseReceiver, asyncore.dispatcher):

    """
    Receiver, in the case of TCP this can be seen as a server instance
    It is bound to the specified address and listening for incoming
    connections and data
    """

    can_send = True

    def __init__(self, host, port):
        BaseReceiver.__init__(self)
        asyncore.dispatcher.__init__(self, map=make_map(host, port))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind( (host, port) )
        self.listen(1)
        self.connections = []
        self.host = host
        self.port = port

    def handle_accept(self):
        conn, addr = self.accept()
        handler = Handler(self.host, self.port, sock=conn)
        handler.dispatcher = self
        handler.on("process-data", self.receive)
        self.connections.append(handler)

    def readable(self):
        self.time = time.time()
        return True

    def send(self, data):
        for handler in self.connections:
            handler.push("%s%s" % (data, TERMINATOR))

    def close(self):
        asyncore.dispatcher.close(self)
        for conn in self.connections:
            conn.close()
        self.connections = []

    def close_inactive(self, delay=60):
        self.connections = [c for c in self.connections if c.is_active(self.time, delay)]

class Sender(BaseSender):

    # direct connection, meaning sender can receive responses
    # directly, so we flag it that it can_receive data
    can_receive = True

    def __init__(self, host, port):
        BaseSender.__init__(self)
        self.handler = Handler(host, port)
        self.handler.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handler.connect( (host, port) )

        if self.can_receive:
            self.handler.on("process-data", self.receive)

    def send(self, data):
        self.handler.push("%s%s" % (data, TERMINATOR))

    def close(self):
        self.handler.close()


# register tcp scheme sender
@register('tcp')
def sender(u):
    return Sender(u.hostname, u.port)

# register tcp scheme receiver
@register('tcp')
def receiver(u):
    return Receiver(u.hostname, u.port)

@register('tcp')
def poller(u):
    if (u.hostname, u.port) not in pollers:
        pollers[(u.hostname, u.port)] = Poller(u.hostname, u.port)
    return pollers[(u.hostname, u.port)]
