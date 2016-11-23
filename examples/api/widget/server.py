import xbahn.api
import xbahn.connection
import xbahn.shortcuts

import signal

# we are going to need a server class to register
# our widget on.
class Server(xbahn.api.Server):
    pass

# We register a widget on our server with the 
# name 'demo', the client will need to use the 
# same name when defining it's widget
@Server.widget('demo')
class DemoWidget(xbahn.api.Widget):

    num = 0

    @xbahn.api.expose
    def set_number(self, num):
        """
        Something for our client widget to call
        """
        self.num = num

    @xbahn.api.expose
    def get_number(self):
        """
        Returns the value in self.num
        """
        return self.num

if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")

    # run api server on connection
    server = xbahn.shortcuts.api_server(connection, Server)

    print("Server running!")

    # clean exit on ctrl+c
    connection.wait_for_signal(signal.SIGINT)
