import xbahn.connection
import xbahn.connection.link
import xbahn.message

if __name__ == "__main__":

    # connect to api server using zmq REQ sockect over TCP (default)
    connection = xbahn.connection.connect("zmq://0.0.0.0:7050/req")
    link = xbahn.connection.link.Link(send=connection, receive=connection)

    # send message to "person" path
    link.main.send("person", xbahn.message.Message("John Smith"))

    # send message to "address" path
    link.main.send("address", xbahn.message.Message("Some Street, 123"))

    # send message to "address" sub path
    link.main.send("address.usa", xbahn.message.Message("Another Street, 123"))
