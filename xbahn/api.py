from __future__ import print_function
from builtins import str
from builtins import object
from xbahn.mixins import EventMixin, LogMixin
from xbahn.message import Message, ErrorMessage
from xbahn.exceptions import APIError
from xbahn.connection import link, connect, listen

import xbahn.path

import traceback
import uuid
import time
import threading

def expose(fn):
    """
    Decorator that exposes a method to the api
    """
    fn.exposed = True
    return fn


class Base(LogMixin, EventMixin):

    """
    API object base, both server and client extend this

    Keyword arguments:
        - link (connection.Link) - wire api object to this link
        - path (str): xbahn path prefix
    """

    path_default = "base"

    def __init__(self, **kwargs):
        EventMixin.__init__(self)
        self.link = None
        if "link" in kwargs:
            self.wire(kwargs.get("link"))


    def wire(self, link):
        """ wire api to a link """
        self.link = link

    def close(self):
        """ close api object and disconnect the link it's wired to """
        if self.link:
            self.link.close()

class Dispatcher(Base):

    """
    API dispatcher

    Will dispatch function calls from one communicator to
    another

    Attributes:
        - comm (Comm): the comm instance that spawned this dispatcher
        - name (str): name of the function targeted by this dispatcher

    Events:
        - api_error: triggers when self.comm.blocking = True and the api
            returns with an error message.

            Payload:
                * message (Message)
                * error_status (dict):
                    - retry (bool) : set to True in order to retry the call

    """

    def __init__(self, comm, name, **kwargs):
        """
        Arguments:
            - comm (Comm): the comm instance that spawned this dispatcher
            - name (str): name of the function to be dispatched
        """

        self.path = kwargs.get("path","")
        Base.__init__(self, **kwargs)
        self.comm = comm
        self.name = name

    def __call__(self, *args, **kwargs):
        message = self.comm.prepare_message(Message(self.name, *args, **kwargs))

        path = xbahn.path.append("call", self.path)

        if self.comm.blocking:

            # comm is set to blocking, so we want to block until
            # a response is received from the server
            m = self.link.main.send_and_wait(path, message, timeout=self.comm.timeout)

            if "error" in m.meta:

                # an error occured, trigger api_error event, which may
                # set retry to True, in which case try once more before
                # finally failing
                error_status = { "retry" : False }
                self.trigger("api_error", error_status=error_status, message=m)
                if error_status.get("retry") == True:
                    message = self.comm.prepare_message(Message(self.name, *args, **kwargs))
                    m = self.link.main.send_and_wait(path, message, timeout=self.comm.timeout)
            if "error" in m.meta:
                raise APIError(m.meta.get("error"))

            return m.data
        else:
            # otherwise send and immediatly return
            return self.link.main.send("call", message)

class ProxyDispatcher(object):

    def __init__(self, comm, **kwargs):
        self.comm = comm
        self.link = kwargs.get("link")
        self.kwargs = kwargs

    def __nonzero__(self):
        return True

    def __getattr__(self, k):
        return self.comm.dispatcher(self.comm, k, **self.kwargs)

class DispatcherGroup(EventMixin):

    """
    Allows to maintain and access and call functions
    on multiple dispatchers
    """

    def __init__(self):
        super(DispatcherGroup, self).__init__()
        self.items = {}

    def __len__(self):
        return len(self.items.values())

    def __delitem__(self, k):
        self.remove(k)

    def __iter__(self):
        for k,v in self.items.items():
            yield v

    def __contains__(self, k):
        return (k in self.items)

    def __setitem__(self, k, v):
        self.add(k, v)

    def __getitem__(self, k):
        return self.items.get(k)

    def __getattr__(self, k):
        dispatchers = self.items.values()
        def dispatch(*args, **kwargs):
            for dsp in dispatchers:
                fn = getattr(dsp, k)
                fn(*args, **kwargs)
        return dispatch


    def add(self, id, dispatcher):
        if not isinstance(dispatcher, Dispatcher) and not isinstance(dispatcher, ProxyDispatcher) and isinstance(dispatcher, Comm):
            raise ValueError("Only objects of type 'Comm', 'Dispatcher' and 'ProxyDispatcher' may be added")

        self.items[id] = dispatcher
        self.trigger("add", id=id, dispatcher=dispatcher)


    def remove(self, id):
        if id not in self.items:
            raise KeyError("dispatcher with id %s not found" % id)
        dispatcher = self.items.get(id)
        del self.items[id]
        self.trigger("remove", id=id, dispatcher=dispatcher)


    def filter(self, **filters):

        filtered = DispatcherGroup()
        for id, dsp in self.items.items():
            add = True
            for f,v in filters.items():
                if getattr(dsp, f, None) != v:
                    add = False
            if add:
                filtered[id] = dsp

        return filtered




class Comm(Base):

    """
    API Communicator class, used as base for both client and server
    classes

    Attributes:

        - blocking (bool): if True all request made with this communicator
            will block until they receive a response
        - timeout (flaot): if blocking is True this specifies a timeout for
            blocking requests
        - debug (bool): if True error responses sent over the api will contain
            a full traceback
        - path (str): xbahn path prefix for all api requests this communicator makes
        - handlers (list): list of api handlers attached to this communicator
    """


    class widget(object):
        """
        Decorator to register a widget for this Communicator class

        Attributes:
            - widgets (dict): holds widgets registered to this communicator
                via it's widget decorator
        """

        widgets = {}
        path = "widgets"

        def __init__(self, name):
            """
            Arguments:
                - name (str): name of the widget
            """
            self.name = name

        def __call__(self, fn):
            self.widgets[self.name] = fn
            fn.name = self.name
            return fn

        def __getitem__(self, k):
            return self.widgets.get(k)

    timeout = 0
    path_default = "comm"

    def __init__(self, **kwargs):
        """
        Keyword arguments:
            - blocking (bool, False): if set to True, all dispatches will block until they
                receive a response
            - timeout (float, 0.0): if greater than zero any server responses longer than
                the timeout will raise a timeout error
            - debug (bool, False): if true, error responses over the api will contain a
                full trace log
                the complete message object, if false dispatched methods will return
                the message.data content
            - path (str): xbahn path
            - handlers (list): list of api handler instances to attach to this communicator
        """
        self.path = kwargs.get("path", self.path_default)

        self.handlers = []

        if "handlers" in kwargs:
            handlers = kwargs.get("handlers")
            if type(handlers) != list:
                raise ValueError("handlers needs to be list of api Handler instances")
            for handler in handlers:
                self.add_handler(handler)

        super(Comm, self).__init__(**kwargs)
        self.blocking = bool(kwargs.get("blocking", True))
        self.timeout = float(kwargs.get("timeout", 0))
        self.debug = bool(kwargs.get("debug", False))
        self.widgets = {}

    def __getattr__(self, k):
        return self.dispatcher(self, k, link=self.link)

    def add_handler(self, handler):
        if handler in self.handlers:
            raise AssertionError("Handler already attached to this communicator")
        self.handlers.append(handler)

    def prepare_message(self, message):
        """
        Prepares the message before sending it out

        Returns:
            - message.Message: the message
        """

        message.meta.update(path=self.path)

        for handler in self.handlers:
            handler.outgoing(message, self)

        return message


    def on_receive(self, message=None, wire=None, event_origin=None):

        """
        event handler bound to the receive event of the
        link the server is wired too.

        Arguments:
            - message (message.Message): incoming message

        Keyword arguments:
            - event_origin (connection.Link)
        """

        self.trigger("before_call", message)

        fn_name = message.data
        pmsg = self.prepare_message

        try:
            for handler in self.handlers:
                handler.incoming(message, self)

            fn = self.get_function(fn_name, message.path)
        except Exception as inst:
            wire.respond(message, ErrorMessage(str(inst)))
            return

        if callable(fn) and getattr(fn, "exposed", False):
            try:
                r = fn(*message.args, **message.kwargs)
                if isinstance(r,Message):
                    wire.respond(message, pmsg(r))
                else:
                    wire.respond(message, pmsg(Message(r)))
            except Exception as inst:
                if self.debug:
                    wire.respond(message, pmsg(ErrorMessage(str(traceback.format_exc()))))
                else:
                    wire.respond(message, pmsg(ErrorMessage(str(inst))))
        else:
            wire.respond(
                message,
                pmsg(
                    ErrorMessage("action '%s' not exposed on API (%s)" % (fn_name, self.__class__.__name__)))
                )

        self.trigger("after_call", message)

    def get_function(self, name, path):
        widget_path = xbahn.path.append(self.path, "call", self.widget.path)

        if xbahn.path.match(widget_path, path):
            widget_name, client_id, widget_id = tuple(xbahn.path.tail(widget_path, path))


            if widget_name not in self.widgets:
                raise APIError("Widget instance not found on server (1)")

            widget_id = xbahn.path.append(client_id, widget_id)

            if widget_id not in self.widgets[widget_name]:
                raise APIError("Widget instance not found on server (2)")

            return getattr(self.widgets[widget_name][widget_id], name, None)
        elif path == xbahn.path.append(self.path, "call"):
            return getattr(self, name, None)
        else:
            raise AttributeError("Unknown call route")

    def wire(self, link):
        super(Comm, self).wire(link)
        self.link.on("receive_%s" % xbahn.path.append(self.path,"call"), self.on_receive)

    def has_widget(self, name, widget_id):
        return name in self.widgets and widget_id in self.widgets[name]

    def store_widget(self, widget):
        if widget.name not in self.widgets:
            self.widgets[widget.name] = DispatcherGroup()
        self.widgets[widget.name][widget.id] = widget

    def make_widget(self, id, name, dispatcher=None, **kwargs):
        if self.has_widget(name, id):
            return self.widgets[name][id]
        if name not in self.widget.widgets:
            return Widget(self, dispatcher=dispatcher)
        return self.widget.widgets[name](self, id, dispatcher=dispatcher, **kwargs)


    @expose
    def request_widget(self, name, id):
        self.log_debug("Got widget request %s -> %s" % (name, id))
        if name in self.widgets:
            if id in self.widgets[name]:
                widget = self.widgets[name][id]
                self.attach_remote(
                    widget.id,
                    widget.remote_name,
                    remote_name=widget.name,
                    **widget.init_kwargs
                )



class Server(Comm):

    """
    API Server
    """
    dispatcher = Dispatcher

    def __repr__(self):
        return "API-SRV"

    def wire(self, link):
        super(Server, self).wire(link)

    @expose
    def obtain_client_id(self):
        return "$"

    @expose
    def attach_remote(self, id, name, **kwargs):
        widget = self.make_widget(
            id,
            name,
            **kwargs
        )
        self.store_widget(widget)

class ClientAwareServer(Server):

    """
    API Server that keeps track of connected clients
    allowing for independent two-way communication

    Attributes:
        - clients (DispatcherGroup): map of connected client wires
        - inactive_timeout (float=0.0): clients that have not interacted
            with the server in the specified timeframe will be closed and
            removed.
        - time (float): unix timestamp of last time cleanup was run

    Events:
        - new_client: called whenever a new client makes contact with
            the server

            payload:
                - client (Comm): client dispatcher
                - client_id (str): client id
    """

    def __init__(self, **kwargs):
        self.clients = DispatcherGroup()
        super(ClientAwareServer, self).__init__(**kwargs)
        self.inactive_timeout = float(kwargs.get("inactive_timeout",0.0))
        self.time = time.time()

        t = threading.Thread(target=self.cleanup)
        t.daemon = True
        t.start()


    def wire(self, link):
        super(ClientAwareServer, self).wire(link)
        self.on("before_call", self.store_client)
        self.on("after_call", self.cleanup)

    @expose
    def obtain_client_id(self):
        id = str(uuid.uuid4())
        n = 0
        while id in self.clients:
            id = str(uuid.uuid4())
            n += 1
            if n > 10000:
                raise IOError("Unable to generate unique client id (10k tries)")
        return id

    def cleanup(self):
        """
        removes inactive clients (will be run in its own thread, about once
        every second)
        """

        while self.inactive_timeout > 0:
            self.time = time.time()

            keys = []

            for key, client in self.clients.items.items():
                t = getattr(client, "active_at", 0)
                if t > 0 and self.time - t > self.inactive_timeout:
                    client.kwargs["link"].disconnect()
                    keys.append(key)

            for key in keys:
                self.log_debug("Removing client (inactive): %s" % key)
                del self.clients[key]

            time.sleep(1)


    def store_client(self, message, event_origin=None):
        if message.meta.get("remote") and message.meta.get("client"):
            client_id = message.meta.get("client")
            if client_id and client_id not in self.clients:
                remote = message.meta.get("remote")
                self.log_debug("Establishing client wire: %s -> %s" % (client_id, remote))

                conn_type, addr = tuple(remote.split("->"))
                if conn_type == "connect":
                    connection = connect(addr)
                elif conn_type == "listen":
                    connection = listen(addr)
                else:
                    self.log_error("Unknown connection type supplied in 'remote' value in client message: %s" % conn_type)
                    return

                client_link = link.Link()
                client_wire = client_link.wire(
                    "main",
                    send=connection,
                    receive=connection
                )
                self.clients[client_id] = ProxyDispatcher(self, link=client_link)
                self.clients[client_id].active_at = self.time
                self.log_debug("Established client wire! (%s)" % client_id)
                self.trigger("new_client", client=self.clients[client_id], id=client_id)
            elif client_id:
                self.clients[client_id].active_at = self.time


    def __getitem__(self, k):
        if k in self.clients:
            return self.clients[k]
        raise KeyError("Client not found: %s", k)

class WidgetAwareServer(ClientAwareServer):

    def wire(self, link):
        super(WidgetAwareServer, self).wire(link)
        self.clients.on("remove", self.on_client_remove)

    def on_client_remove(self, id=None, dispatcher=None, event_origin=None):
        for widgets in self.widgets.values():
            keys = []
            for key in widgets.items.keys():
                if key.find("%s." % id) == 0:
                    keys.append(key)
            for key in keys:
                self.log_debug("Removing widget %s" % key)
                del widgets[key]

    @expose
    def detach_remote(self, id, name):
        """
        destroy remote instance of widget

        Arguments:
            - id (str): widget id
            - name (str): widget type name
        """

        if name in self.widgets:
            if id in self.widgets[name]:
                del self.widgets[name]


    @expose
    def attach_remote(self, id, name, **kwargs):
        """
        create remote instance of widget

        Arguments:
            - id (str): widget id
            - name (str): widget type name

        Keyword Arguments:
            - any further arguments you wish to pass
                to the widget constructor

        """

        client_id = id.split(".")[0]

        widget = self.make_widget(
            id,
            name,
            dispatcher=ProxyDispatcher(
                self,
                link=getattr(self.clients[client_id], "link", None)
            ),
            **kwargs
        )
        self.store_widget(widget)
        self.log_debug("Attached widget: %s" % id)


class Client(Comm):

    """
    API Client

    Can connect to an api server and dispatch function calls to it

    Attributes:
        - id (str): unique id for this client instance
        - dispatcher: which Dispatcher class to use for method dispatch
    """

    dispatcher = Dispatcher

    class widget(Comm.widget):

        """
        Decorator to register a widget for this Client class
        """

        widgets = {}

        def __init__(self, name, remote_name=None):
            """
            Keyword Arguments:
                - remote_name (str): name of the widget (server side), defaults to <name>
            """
            Comm.widget.__init__(self, name)
            self.remote_name = remote_name or name

        def __call__(self, fn):
            Comm.widget.__call__(self, fn)
            fn.remote_name = self.remote_name
            return fn


    def __init__(self, **kwargs):
        self.id = None
        super(Client, self).__init__(**kwargs)

    def __repr__(self):
        return "API-CLI-%s" % self.id

    def wire(self, link):
        super(Client, self).wire(link)
        self.id = self.obtain_client_id()

    def prepare_message(self, message):
        message.meta.update(client=self.id)
        return super(Client, self).prepare_message(message)


class Widget(EventMixin):

    """
    API Widget

    An api widget is a modular object that lives on an established
    api communication, it can have its own methods exposed separate
    from the comm's methods

    Attributes:
        - comm (Comm): instance that spawned this widget
        - id (str)
        - group (str): widget group name
        - dispatcher (Comm, Dispatcher, ProxyDispatcher)
        - init_kwargs (dict): kwargs passed to the ctor
        - remote_name (str)
        - name (str)
    """

    def __init__(self, comm, id, dispatcher=None, **kwargs):
        super(Widget, self).__init__()
        self.comm = comm
        self.group = kwargs.get("group")
        self.dispatcher = dispatcher
        self.init_kwargs = kwargs

        if "remote_name" in kwargs:
            self.remote_name = kwargs.get("remote_name")

        if isinstance(comm, Client):
            self.id = xbahn.path.append(comm.id, id)
            # widget is attached to a client, try to attach at server
            try:
                self.comm.attach_remote(self.id, self.remote_name, remote_name=self.name, **kwargs)
            except APIError as inst:
                print(inst)

            self.dispatcher = ProxyDispatcher(
                comm,
                link=comm.link
            )
            comm.store_widget(self)
        elif isinstance(comm, Server):
            self.id = id

        self.path = xbahn.path.append(comm.widget.path, self.remote_name, self.id)


        if self.dispatcher:
            self.dispatcher.kwargs['path']  = self.path

        self.setup()

    def __getattr__(self, k):
        if self.dispatcher:
            dispatcher = getattr(self.dispatcher, k)
            dispatcher.on("api_error", self.on_api_error)
            return dispatcher
        else:
            return getattr(self.comm, k)

    def setup(self):
        """
        Override for extra widget setup

        Is called after __init__ has completed
        """
        pass

    def on_api_error(self, error_status=None, message=None, event_origin=None):

        """
        API error handling
        """
        if message.meta["error"].find("Widget instance not found on server") > -1:
            # widget is missing on the other side, try to re-attach
            # then try again
            error_status["retry"] = True
            self.comm.attach_remote(
                self.id,
                self.remote_name,
                remote_name=self.name,
                **self.init_kwargs
            )

class Handler(LogMixin, EventMixin):

    """
    Base API Handler class
    """

    def __init__(self, *args, **kwargs):
        super(Handler, self).__init__()
        self.setup(*args, **kwargs)

    def outgoing(self, message, comm):
        """
        override this to do something to an outgoing message before
        it is sent.

        raising an APIError here will halt sending of the message
        """
        pass

    def incoming(self, message, comm):
        """
        override this to do something to an incoming message before
        it is processed (executed)

        raising an APIError here will halt processing of the message
        """
        pass

    def setup(self, *args, **kwargs):
        """
        override this (instead of __init__) to setup your handler
        """
        pass


class AuthHandler(Handler):

    """
    Very simple auth handler that sends and asks for a plain key
    """

    def setup(self, key, **kwargs):
        if len(key) < 8:
            raise ValueError("Key should be at least 8 characters long")
        self.key = key

    def outgoing(self, message, comm):
        comm.log_debug("AUTH (sending): %s... (truncated)" % self.key[:3])
        message.meta.update(auth=self.key)

    def incoming(self, message, comm):
        comm.log_debug("AUTH (requiring): %s... (truncated)" % self.key[:3])
        if message.meta.get("auth") != self.key:
            raise APIError("Authentication failed.")
