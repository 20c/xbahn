import xbahn.connection
import xbahn.connection.link
import xbahn.message

import signal

if __name__ == "__main__":

    # listen using zmq REP sockect over TCP (default)
    connection = xbahn.connection.listen("zmq://0.0.0.0:7050/rep")
    link = xbahn.connection.link.Link(respond=connection, receive=connection)

    def handle_incoming_person(message=None, wire=None, event_origin=None):
        print("Message arrived", "PERSON", message.data, message.path)

    def handle_incoming_address(message=None, wire=None, event_origin=None):
        print("Message arrived", "ADDRESS", message.data, message.path)

    # handle messages sent to 'person' path
    link.on("receive_person", handle_incoming_person)

    # handle messages sent to 'address' path
    link.on("receive_address", handle_incoming_address)

    print("Server running!")

    # run until ctrl+c
    connection.wait_for_signal(signal.SIGINT)
