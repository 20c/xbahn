import xbahn.api
import xbahn.connection
import xbahn.shortcuts

import signal

class Server(xbahn.api.Server):

    @xbahn.api.expose
    def ping(self):
        """
        Something to call for our client
        """
        return "pong!"

    @xbahn.api.expose
    def multiply(self, a, b):
        """
        Multiply a with b and return result to client
        """
        return int(a) * int(b)


if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")

    # run api server on connection
    server = xbahn.shortcuts.api_server(connection, Server)

    print("Server running!")

    # clean exit on ctrl+c
    connection.wait_for_signal(signal.SIGINT)
