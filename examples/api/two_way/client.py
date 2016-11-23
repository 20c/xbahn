import xbahn.api
import xbahn.connection
import xbahn.shortcuts

class Client(xbahn.api.Client):

    touched = False

    @xbahn.api.expose
    def touch(self):
        """
        Something for the server to call
        """
        self.touched = True
        return True

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

    print("ping!")
    # send "ping" call to server and print the response
    # by default this will block until a response is received or the
    # request fails.
    print(client.ping()) # pong!

    # since the server calls client.touch() every time a new client
    # makes contact, our client should now reflect that
    print("Touched?", client.touched)

    # we are done
    connection_responder.destroy()
