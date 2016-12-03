from future import standard_library
standard_library.install_aliases()
from builtins import object
from xbahn.message import Message
from xbahn.mixins import EventMixin, LogMixin
from xbahn.exceptions import SchemeNotFound

import importlib
import urllib.parse
import threading
import time
import signal
import munge
import munge.codec.all

SCHEMES = {}

CONNECTION_TYPE_SERVER = 1
CONNECTION_TYPE_CLIENT = 2

PREFIXES = 0

class Connection(EventMixin, LogMixin, threading.Thread):

    """
    Base connection class

    Attributes:

        - close_when_ready (bool): if True, connection will attempt
            to close itself the next time it is idle.
        - transport_content_type (str, default="json"): content type
            for message date (munge codec)

    Events:

        - receive: triggered when connection receives a message
            - data (str): raw data
            - message (Message): xbahn message object
            - event_origin (EventMixin): object that triggered
                the event

        - send: triggered when connection has sent a message
            - message (Message): xbahn message object
    """

    def __init__(self, transport_content_type="json"):
        threading.Thread.__init__(self)
        EventMixin.__init__(self)
        self.close_when_ready = False

        self.transport_content_type = transport_content_type

        # munge codec instance from transport_content_type
        self.codecClass = munge.get_codec(transport_content_type)
        self.codec = self.codecClass()


    @property
    def connected(self):
        """
        Should return True if connection is currently connected
        to a host
        """
        return False

    @property
    def bound(self):
        """
        Should return True if connection is currently bound/listening
        on an address
        """
        return False

    @property
    def active(self):
        """
        Returns True if either connected or bound are True
        """
        return self.bound or self.connected

    @property
    def remote(self):
        """
        Should return a string representation of the xbahn url
        that can be used to connect to this listener
        """
        return None

    @property
    def connection_type(self):
        """
        Should return either CONNECTION_TYPE_SERVER or
        CONNECTION_TYPE_CLIENT
        """
        return 0

    @property
    def can_receive(self):
        """
        Should return whether or not this connection can receive
        data
        """
        return True

    @property
    def can_respond(self):
        """
        Should return whether or not this connection can respond
        to incoming data
        """
        return True

    @property
    def can_send(self):
        """
        Should return whether or not this connection can initiate
        requests
        """
        return True

    def make_data(self, message):

        """
        make data string from message according to transport_content_type

        Returns:

            str: message data
        """

        if not isinstance(message, Message):
            return message
        return message.export(self.transport_content_type)

    def make_message(self, data):

        """
        Create a Message instance from data, data will be loaded
        via munge according to the codec specified in the
        transport_content_type attribute

        Returns:

            Message: message object
        """

        data = self.codec.loads(data)
        msg = Message(
            data.get("data"),
            *data.get("args",[]),
            **data.get("kwargs",{})
        )
        msg.meta.update(data.get("meta"))
        self.trigger("make_message", data, msg)
        return msg


    def start(self):
        self.run_level = 1
        super(Connection, self).start()

    def listen(self):
        """
        Should bind the connection
        """
        pass

    def connect(self):
        """
        Should establish connection to host
        """
        pass

    def send(self, message):
        """
        Should send message

        Arguments:
            - message (Message or dict): message to send
        """
        pass

    def close(self):
        """
        Close the connection at the next possible opportunity
        """
        self.close_when_ready = True

    def run(self):
        return

    def stop(self):
        self.run_level = 0

    def finalize_connection(self):
        """
        Finalize your connection in here, called after connect()
        and listen()
        """
        pass

    def receive(self, data):
        """
        Create and return a message from data, also triggers the
        **receive** event

        Returns:

            - Message: message object
        """
        self.log_debug("Received: %s" % (data))
        message =  self.make_message(data)
        self.trigger("receive", data=data, message=message)
        return message

    def wait_for_signal(self, *signals):
        conn = self
        def shutdown(signal, frame):
            conn.close()
        for s in signals:
            signal.signal(s, shutdown)
        while self.active:
            time.sleep(0.1)


class Receiver(EventMixin):

    """
    Base Receiver class
    """

    def __init__(self, connection):
        super(Receiver, self).__init__()
        self.connection = connection
        self.connection.on("receive", self.receive)

    def receive(self, data, event_origin=None, responder=None):
        self.trigger("receive", data, responder=responder)


class Sender(EventMixin):

    """
    Base Sender class
    """

    def __init__(self, connection):
        super(Sender, self).__init__()
        self.connection = connection

    def send(self, data):
        self.connection.send(data)
        self.trigger("send", data)


class register(object):

    """
    Decorator

    Register a sender or receiver class to a scheme

    scheme <str> scheme name (eg. 'tcp', 'qpid')
    """

    def __init__(self, scheme):
        self.scheme = scheme
    def __call__(self, fnc):
        scheme = self.scheme
        if scheme not in SCHEMES:
            SCHEMES[scheme] = {}
        SCHEMES[scheme][fnc.__name__] = fnc
        return fnc

def url_to_resources(url):
    o = urllib.parse.urlparse(url)

    if o.scheme not in SCHEMES:
        importlib.import_module("xbahn.connection.%s" % o.scheme)

    if o.scheme not in SCHEMES:
        raise SchemeNotFound(o.scheme)

    rv = { "url" : o }
    rv.update(SCHEMES[o.scheme])
    return rv

def receiver(url, **kwargs):
    """
    Return receiver instance from connection url string

    url <str> connection url eg. 'tcp://0.0.0.0:8080'
    """
    res = url_to_resources(url)
    fnc = res["receiver"]
    return fnc(res.get("url"), **kwargs)

def sender(url, **kwargs):
    """
    Return sender instance from connection url string

    url <str> connection url eg. 'tcp://0.0.0.0:8080'
    """

    res = url_to_resources(url)
    fnc = res["sender"]
    return fnc(res.get("url"), **kwargs)

def connection(url, prefix=None, **kwargs):
    res = url_to_resources(url)
    fnc = res["connection"]
    return fnc(res.get("url"), prefix=prefix, **kwargs)

def listener(url, prefix=None, **kwargs):
    res = url_to_resources(url)
    fnc = res["listener"]
    return fnc(res.get("url"), prefix=prefix, **kwargs)

def listen(url, prefix=None, **kwargs):
    """
    bind and return a connection instance from url

    arguments:
        - url (str): xbahn connection url
    """
    return listener(url, prefix=get_prefix(prefix), **kwargs)

def connect(url, prefix=None, **kwargs):
    """
    connect and return a connection instance from url

    arguments:
        - url (str): xbahn connection url
    """
    return connection(url, prefix=get_prefix(prefix), **kwargs)

def get_prefix(prefix):
    global PREFIXES
    if prefix is None:
        PREFIXES += 1
        return "$%d" % (PREFIXES)
    return prefix

def close(*entities):
    # close senders first
    for ent in entities:
        if isinstance(ent, Sender):
            ent.close()

    # close receivers second
    for ent in entities:
        if not isinstance(ent, Sender):
            ent.close()

