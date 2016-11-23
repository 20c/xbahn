import time

import xbahn.path
from xbahn.mixins import EventMixin, LogMixin
from xbahn.connection import receiver, sender
from xbahn.message import Message

LINK_NAME_COUNTER = 0
def get_link_name():
    global LINK_NAME_COUNTER
    LINK_NAME_COUNTER += 1
    return "lnk-%d" % LINK_NAME_COUNTER


class Wire(LogMixin, EventMixin):

    def __init__(self, receive=None, send=None, respond=None):
        EventMixin.__init__(self)

        self.connection_receive = receive
        self.connection_respond = respond
        self.connection_send = send
        self.meta = {}
        self.name = ""

        if receive:
            receive.on("receive", self.on_receive)

    def __repr__(self):
        return "WIRE-%s" % self.name

    def disconnect(self):
        """
        Close all connections that are set on this wire
        """

        if self.connection_receive:
            self.connection_receive.close()
        if self.connection_respond:
            self.connection_respond.close()
        if self.connection_send:
            self.connection_send.close()

    def send(self, path, message):

        if message.path:
            message.meta.update(path=xbahn.path.append(message.path, path))
        else:
            message.meta.update(path=path)

        if self.meta:
            message.meta.update(**self.meta)

        if message.has_callbacks("response"):
            #message is expecting response
            self.on("response_%s" % message.id, message.attach_response, once=True)
            self.on("response_%s" % message.id, message.response, once=True)

        self.connection_send.send(message)

    def send_and_wait(self, path, message, timeout=0, responder=None):
        """
        Send a message and block until a response is received. Return response message
        """

        message.on("response", lambda x,event_origin,source:None, once=True)

        if timeout > 0:
            ts = time.time()
        else:
            ts = 0
        sent = False

        while not message.response_received:
            if not sent:
                self.send(path, message)
                sent = True
            if ts:
                if time.time() - ts > timeout:
                    raise exceptions.TimeoutError("send_and_wait(%s)"%path, timeout)

        return message.response_message


    def respond(self, to_message, message, path=None):
        if not path:
            path = "xbahn.response.%s" % to_message.id
        message.meta.update(response_id=to_message.id, path=path)

        if self.meta:
            message.meta.update(**self.meta)

        self.connection_respond.respond(to_message, message)

    def on_receive(self, message=None, data=None, event_origin=None):
        # trigger events for message received
        self.trigger("receive", message=message)

        for p in xbahn.path.walk(message.path):
            self.trigger("receive_%s" % p, message=message)


        if message.response_id:
            # trigger events for response received
            self.trigger("response", message=message)
            self.trigger("response_%s" % message.response_id, message=message)


class Link(LogMixin, EventMixin):

    """
    Manages receiving and sending to one or more connection

    Attributes:

        - name (str): the links name
        - main (Wire): the main wire, is set automatically during the
            first wire() call or by passing "main" as the name during wire()
    """

    def __init__(self, name=None, **kwargs):

        """

        Keyword Arguments:
            - name (str): name for this link, if not provided a unique
                default value will be used
            - receive (Connection): if supplied a "main" wire will be
                established using this connection as a receiver
            - send (Connection): if supplied a "main" wire will be
                established using this connection as a sender
            - respond (Connection): if supplied a "main" wire will be
                established using this connection as a responder
        """

        EventMixin.__init__(self)
        self.name = name or get_link_name()
        self.main = None

        if "receive" in kwargs or "send" in kwargs or "respond" in kwargs:
            self.wire(
                "main",
                receive=kwargs.get("receive"),
                send=kwargs.get("send"),
                respond=kwargs.get("respond")
            )


    def __repr__(self):
        return "LINK: %s" % self.name

    def wire(self, name, receive=None, send=None, respond=None, **kwargs):

        """
        Wires the link to a connection. Can be called multiple
        times to set up wires to different connections

        After creation wire will be accessible on the link via its name
        as an attribute.

        You can undo this action with the cut() method

        Arguments:

            - name (str): unique name for the wire

        Keyword Arguments:

            - receive (Connection): wire receiver to this connection
            - respond (Connection): wire responder to this connection
            - send (Connection): wire sender to this connection
            - meta (dict): attach these meta variables to any message
                sent from this wire

        Returns:

            - Wire: the created wire instance
        """

        if hasattr(self, name) and name != "main":
            raise AttributeError("cannot use '%s' as name for wire, attribute already exists")

        if send:
            self.log_debug("Wiring '%s'.send: %s" % (name, send))
        if respond:
            self.log_debug("Wiring '%s'.respond: %s" % (name, respond))
        if receive:
            self.log_debug("Wiring '%s'.receive: %s" % (name, receive))

        wire = Wire(receive=receive, send=send, respond=respond)
        wire.name = "%s.%s" % (self.name, name)
        wire.meta = kwargs.get("meta",{})
        wire.on("receive", self.on_receive)
        setattr(self, name, wire)

        if not self.main:
            self.main = wire

        return wire

    def cut(self, name, disconnect=False):

        """
        Cut a wire (undo a wire() call)

        Arguments:

            - name (str): name of the wire

        Keyword Arguments:

            - disconnect (bool): if True also disconnect all connections on the
                specified wire
        """

        wire = getattr(self, name, None)
        if wire and isinstance(wire, Wire):
            if name != "main":
                delattr(self, name)
            if disconnect:
                wire.disconnect()
            wire.off("receive", self.on_receive)
            if self.main == wire:
                self.main = None
                self.set_main_wire()

    def set_main_wire(self, wire=None):

        """
        Sets the specified wire as the link's main wire
        This is done automatically during the first wire() call

        Keyword Arguments:

            - wire (Wire): if None, use the first wire instance found

        Returns:

            - Wire: the new main wire instance
        """

        if not wire:
            for k in dir(self):
                if isinstance(getattr(self, k), Wire):
                    wire = getattr(self, k)
                    break
        elif not isinstance(wire, Wire):
            raise ValueError("wire needs to be a Wire instance")

        if not isinstance(wire, Wire):
            wire = None

        self.main = wire
        return wire

    def wires(self):
        """
        Yields name (str), wire (Wire) for all wires on
        this link
        """

        for k in dir(self):
            if isinstance(getattr(self, k), Wire):
                yield k, getattr(self, k)

    def disconnect(self):
        """
        Cut all wires and disconnect all connections established on this link
        """

        for name, wire in self.wires():
            self.cut(name, disconnect=True)


    def on_receive(self, message=None, event_origin=None):

        # trigger events for message received
        self.trigger("receive", message=message, wire=event_origin)
        for p in xbahn.path.walk(message.path):
            self.trigger("receive_%s" % p, message=message, wire=event_origin)

        if message.response_id:
            # trigger events for response received
            self.trigger("response", message=message, wire=event_origin)
            self.trigger("response_%s" % message.response_id, message=message, wire=event_origin)
