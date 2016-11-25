import xbahn.connection
import xbahn.connection.link
import xbahn.message

import signal

if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")
    link = xbahn.connection.link.Link(respond=connection, receive=connection)

    def handle_incoming_message(message=None, wire=None, event_origin=None):
        print(message.data) # Test
        print(message.args) # ["an arg"]
        print(message.kwargs) # {"something":"extra"}
        # send response
        wire.respond(message, xbahn.message.Message("Message '%s' received!" % message.data))

    # bind handle_incoming_message to receive event 
    link.on("receive", handle_incoming_message)

    print("Server running!")

    # run until ctrl+c
    connection.wait_for_signal(signal.SIGINT)
