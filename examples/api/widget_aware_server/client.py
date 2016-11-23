import xbahn.shortcuts
import xbahn.connection
import xbahn.api

# we are going to need a client class to register
# our widget on
class Client(xbahn.api.Client):
    pass

# We register a widget on our client with the name
# 'demo', this corresponse with name for the widget
# we defined on the server side
@Client.widget('demo')
class DemoWidget(xbahn.api.Widget):

    _slapped = False

    @xbahn.api.expose
    def slapped(self):
        """
        Returns self._slapped
        """
        return self._slapped

    @xbahn.api.expose
    def slap(self):
        """
        Something for the server widget to call
        """
        self._slapped = True

if __name__ == "__main__":

    # connect to api server using zmq REQ sockect over TCP (default)
    connection = xbahn.connection.connect("zmq://0.0.0.0:7050/req")

    # since this client should also be able to receive messages and respond
    # as part of the two-way communcation, we need to define a secondary
    # connection for that, using zmq REP socket over TCP (default)
    connection_responder = xbahn.connection.listen("zmq://0.0.0.0:7051/rep")

    # run client on our connections
    client = xbahn.shortcuts.api_client_two_way(
        connection,
        connection_responder,
        client_class=Client
    )

    # instantiate widget using the client
    widget_a = DemoWidget(client, "widget_a")

    # call "poke" on the server widget
    widget_a.poke()

    # during poke() the server should have called slap() on the client widget
    print("Slapped (a)?", widget_a.slapped()) # True (called local)
    print("Poked (a)?", widget_a.poked()) # True (called remote)

    # lets connect another widget on a separate client
    client_b = xbahn.shortcuts.api_client(connection, client_class=Client)
    widget_a_b = DemoWidget(client_b, "widget_a")
    # Widget aware servers are also aware of clients and each client will
    # maintain its own widget instance on the remote side
    print("Poked (b)?", widget_a_b.poked()) # False (called remote)

    # we are done
    connection_responder.destroy()
