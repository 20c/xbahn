import xbahn.api
import xbahn.connection
import xbahn.shortcuts

import signal

# we are going to need a server class to register
# our widget on. This time we use the WidgetAwareServer
# as base
class Server(xbahn.api.WidgetAwareServer):
    pass

# We register a widget on our server with the 
# name 'demo', the client will need to use the 
# same name when defining it's widget
@Server.widget('demo')
class DemoWidget(xbahn.api.Widget):

    _poked = False

    @xbahn.api.expose
    def poked(self):
        """
        Returns self._poked
        """
        return self._poked

    @xbahn.api.expose
    def poke(self):
        """
        Something for the client widget to call
        """
        self._poked = True

        # now call slap() on the client
        self.slap()


if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")

    # run api server on connection
    server = xbahn.shortcuts.api_server(connection, Server)
    print("Server running!")

    # clean exit on ctrl+c
    connection.wait_for_signal(signal.SIGINT)
