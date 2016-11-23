from __future__ import absolute_import, unicode_literals
from builtins import str

from xbahn.connection import (
    register,
    Receiver as BaseReceiver,
    Sender as BaseSender,
    Connection as BaseConnection,
)

from threading import Lock
from xbahn.message import Message
import urllib.parse

import time

try:
    import zmq
except ImportError:
    pass

instance = {}
connections = {}

def context():
    if "context" not in instance:
        instance["context"] = zmq.Context()
    return instance["context"]

def config_from_url(u, **kwargs):

    """
    Returns dict containing zmq configuration arguments
    parsed from xbahn url

    Arguments:

        - u (urlparse.urlparse result)

    Returns:

        dict:
            - id (str): connection index key
            - typ_str (str): string representation of zmq socket type
            - typ (int): zmq socket type (PUB, SUB, REQ, REP, PUSH, PULL)
            - topic (str): subscription topic
            - url (str): url to use with zmq's bind function
    """

    path = u.path.lstrip("/").split("/")
    if len(path) > 2 or not path:
        raise AssertionError("zmq url format: zmq://<host>:<port>/<pub|sub>/<topic>")

    typ = path[0].upper()

    try:
        topic = path[1]
    except IndexError as _:
        topic = ''

    param = dict(urllib.parse.parse_qsl(u.query))

    #FIXME: should come from schema, maybe zmq+tcp:// ?
    transport = param.get("transport", "tcp")

    _id = "%s-%s-%s-%s" % (typ, topic, transport, u.netloc)
    if kwargs.get("prefix") is not None:
        _id = "%s-%s" % (kwargs.get("prefix"), _id)

    return {
        "id" : _id,
        "typ_str" : typ,
        "typ" : getattr(zmq, typ),
        "topic" : topic,
        "transport" : transport,
        "url" : "%s://%s" % (transport, u.netloc)
    }




class Connection(BaseConnection):

    def __init__(self, **kwargs):
        super(Connection, self).__init__()
        for k,v in list(kwargs.items()):
            if k in ["id","typ","typ_str","url","topic","transport"]:
                setattr(self, k, v)
        self.context = context()
        self.socket = None

        self._waiting = False

    def __repr__(self):
        return "CONN %s"  % (self.id)

    @property
    def waiting(self):
        return self._waiting

    @property
    def connected(self):
        return self.socket and not self.socket.closed

    @property
    def bound(self):
        return self.socket and not self.socket.closed

    @property
    def remote(self):
        if self.topic:
            t = "/%s" % self.topic
        else:
            t = ""

        if self.typ == zmq.PUB:
            typ_str = "sub"
        elif self.typ == zmq.SUB:
            typ_str = "pub"
        elif self.typ == zmq.PUSH:
            typ_str = "pull"
        elif self.typ == zmq.PULL:
            typ_str = "push"
        elif self.typ == zmq.REP:
            typ_str = "req"
        elif self.typ == zmq.REQ:
            typ_str = "rep"

        if self.bound:
            conn_type = "connect"
        else:
            conn_type = "listen"

        return "%s->zmq://%s/%s%s?transport=%s" % (
            conn_type,
            self.url.split("//")[1], typ_str, t, self.transport
        )


    def connect(self):

        self.log_debug("Connecting ...")

        if self.connected:
            raise AssertionError("connection is already established")

        self.socket = self.context.socket(self.typ)
        self.socket.connect(self.url)
        self.finalize_connection()

        self.log_debug("Connected!")

        self.start()

    def listen(self):

        self.log_debug("Binding listener ...")

        if self.bound:
            raise AssertionError("connection is already listening")

        self.socket = self.context.socket(self.typ)
        self.socket.bind(self.url)
        self.finalize_connection()

        self.log_debug("Bound!")

        self.start()

    def receive(self):
        self.log_debug("Attempting to receive ...")

        try:
            data = self.socket.recv_string()
        except zmq.ZMQError as inst:
            if str(inst).find("operation on non-socket") > -1:
                self.destroy()
                return Message(None)
            raise

        if self.topic:
            data = data.lstrip("%s "%self.topic)
        return super(Connection, self).receive(data)

    def send(self, message):
        data = self.make_data(message)
        if self.topic:
            data = "%s %s" % (self.topic, data)
        self.log_debug("Attempting to send ...")
        self.socket.send_string(data)
        self.trigger("send", data)
        self.log_debug("Sent: %s" % (data))

    def close(self):
        if not self.connected and not self.bound:
            return
        if not self.waiting:
            self.destroy()
        else:
            self.close_when_ready = True

    def destroy(self):
        self.log_debug("Destroying connection")
        if not self.socket.closed:
            self.socket.close()
        self.stop()
        try:
            del connections[self.id]
        except KeyError as inst:
            pass


class REQ_Connection(Connection):

    """
    REQ zmq connection handler

    Can initiate send, then has to wait for response
    before it can send again

    Attributes:

        - waiting (bool): if true, is currently waiting on response
            from previous call to send()
    """

    def __init__(self, **kwargs):
        super(REQ_Connection, self).__init__(**kwargs)
        self._waiting = False

    connection_type = "client"

    def send(self, data):
        self._waiting = True
        super(REQ_Connection, self).send(data)
        self.receive()
        self._waiting = False
        if self.close_when_ready:
            self.destroy()



class REP_Connection(Connection):

    """
    REP zmq connection handler

    Can only send in response to incoming messages

    Attributes:

        - waiting (bool): if True, is currently waiting for messages and
            not ready to send
    """

    def __init__(self, **kwargs):
        super(REP_Connection, self).__init__(**kwargs)
        self._waiting = True

    def run(self):
        self.log_debug("Poller starting!")
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        while self.run_level==1:
            if not self.active:
                break

            try:
                socks = dict(self.poller.poll(timeout=250))
            except zmq.ZMQError as inst:
                if str(inst).find("operation on non-socket"):
                    if not self.socket.closed:
                        self.destroy()
                    self.stop()
                    return
                else:
                    raise

            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                try:
                    self.receive()
                except Exception as inst: #FIXME
                    pass
            if self.close_when_ready:
                self.destroy()

    def receive(self):
        message = super(REP_Connection, self).receive()
        self._waiting = False
        if not message.responded:
            self.respond(message, Message(None))
        self._waiting = True
        return message

    def respond(self, to_message, message):
        self.send(message)
        to_message.responded = True


class SUB_Connection(REP_Connection):

    """
    ZMQ SUB connection handler, can only receive
    """

    def finalize_connection(self):
        if self.topic:
            self.log_debug("Subscribing to '%s'" % self.topic)
            self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)

    def send(self, message):
        pass

    def respond(self, to_message, message):
        pass


class PUB_Connection(Connection):

    def close(self):
        self.destroy()


class PUSH_Connection(PUB_Connection):

    connection_type = "server"

    def send(self, data):
        Connection.send(self, data)



class PULL_Connection(SUB_Connection):

    connection_type = "client"

    def finalize_connection(self):
        pass

    def receive(self):
        Connection.receive(self)

    def response(self):
        pass


class Receiver(BaseReceiver):
    pass

class Sender(BaseSender):
    pass


CONNECTION_CLASSES = {
    zmq.REQ : REQ_Connection,
    zmq.REP : REP_Connection,
    zmq.PUSH : PUSH_Connection,
    zmq.PULL : PULL_Connection,
    zmq.PUB : PUB_Connection,
    zmq.SUB : SUB_Connection
}

@register('zmq')
def connection(u, **kwargs):
    cfg = config_from_url(u, **kwargs)
    key = cfg.get("id")


    if key not in connections:
        cls = CONNECTION_CLASSES.get(cfg.get("typ"))
        if not cls:
            raise KeyError("Unknown zmq socket type: %s" % cfg.get("typ_str"))
        connections[key] = cls(**cfg)

    conn = connections.get(key)
    if not conn.connected:
        conn.connect()
    return conn


@register('zmq')
def listener(u, **kwargs):
    cfg = config_from_url(u, **kwargs)
    key = cfg.get("id")

    if key not in connections:
        cls = CONNECTION_CLASSES.get(cfg.get("typ"))
        if not cls:
            raise KeyError("Unknown zmq socket type: %s" % cfg.get("typ_str"))
        connections[key] = cls(**cfg)

    conn = connections.get(key)
    if not conn.bound:
        conn.listen()
    return conn


@register('zmq')
def receiver(u, **kwargs):
    return Receiver(connection(u, **kwargs))


@register('zmq')
def sender(u, **kwargs):
    return Sender(connection(u, **kwargs))

