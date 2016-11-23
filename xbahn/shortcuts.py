"""
Collection of shortcut functions for common operations
"""

import xbahn.api
import xbahn.connection
import xbahn.connection.link

def api_client(connection, client_class=xbahn.api.Client):
    """
    Establishes an API client for one-way communication
    connection with an API Server
    
    Arguments:
        - connection (xbahn.connection.Connection)

    Keyword Arguments:
        - client_class (xbahn.api.Client): if supplied use this class to initantiate
            the client object. If omitted will use xbahn.api.Client.
    
    Returns:
        - client_class: client instance
    """

    return client_class(
        link=xbahn.connection.link.Link(
            # use the connection receive messages (server responses)
            receive=connection,
            # use the connection to send messages (initiate requests to server)
            send=connection
        )
    )


def api_client_two_way(connection, connection_responder, client_class=xbahn.api.Client):
    """
    Establishes an API client for two-way communication
    connection with an API Server
    
    Arguments:
        - connection (xbahn.connection.Connection)
        - connection_responder (xbahn.connection.Connection): This connection will
            be used by the server to send requests to the client

    Keyword Arguments:
        - client_class (xbahn.api.Client): if supplied use this class to initantiate
            the client object. If omitted will use xbahn.api.Client.
    
    Returns:
        - client_class: client instance
    """

    # create connection link instance
    link = xbahn.connection.link.Link()

    # main wire
    link.wire(
        "main",
        receive=connection,
        send=connection,
        # in order to let the server know how to send messages to client
        # we include the "remote" property in the message meta
        meta={
            "remote":connection_responder.remote
        }
    )

    # response wire
    link.wire(
        "responder",
        receive=connection_responder,
        respond=connection_responder
    )

    # run api client on connection
    return client_class(link=link)


def api_server(connection, server_class):
    """
    Establishes an API Server on the supplied connection

    Arguments:
        - connection (xbahn.connection.Connection)
        - server_class (xbahn.api.Server)

    Returns:
        - server_class: server instance
    """

    # run api server on connection
    return server_class(
        link=xbahn.connection.link.Link(
            # use the connection to receive messages
            receive=connection,
            # use the connection to respond to received messages
            respond=connection
        )
    )

