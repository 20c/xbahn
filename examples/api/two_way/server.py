import xbahn.api
import xbahn.connection
import xbahn.shortcuts

import signal

# We extend ClientAwareServer because for two-way communication
# to work, the server needs to be.. well.. aware of the clients
# connected to it
class Server(xbahn.api.ClientAwareServer):

    @xbahn.api.expose
    def ping(self):
        """
        Something to call for our client
        """
        return "pong!"


if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")

    # run api server on connection
    server = xbahn.shortcuts.api_server(connection, Server)

    # every time a new client makes contact call touch() on the client
    server.on("new_client", lambda client, **kw: client.touch())
    print("Server running!")

    # clean exit on ctrl+c
    connection.wait_for_signal(signal.SIGINT)
