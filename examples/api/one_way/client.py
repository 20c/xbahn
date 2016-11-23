import xbahn.shortcuts
import xbahn.connection

if __name__ == "__main__":

    # connect to api server using zmq REQ sockect over TCP (default)
    connection = xbahn.connection.connect("zmq://0.0.0.0:7050/req")

    # run api client on our connection
    client = xbahn.shortcuts.api_client(connection)

    print("ping!")
    # send "ping" call to server and print the response
    # by default this will block until a response is received or the
    # request fails.
    print(client.ping()) # pong!

    # multiply 7 and 6 and print the result
    print("7*6 =",client.multiply(7,6))
