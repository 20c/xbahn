import xbahn.shortcuts
import xbahn.connection
import xbahn.api

# we are going to need a client class to register
# our widget on
class Client(xbahn.api.Client):
    pass

# We register a widget on our client with the name
# 'demo', this corresponse with name for the widget
# we defined on the server side
@Client.widget('demo')
class DemoWidget(xbahn.api.Widget):
    pass

if __name__ == "__main__":

    # connect to api server using zmq REQ sockect over TCP (default)
    connection = xbahn.connection.connect("zmq://0.0.0.0:7050/req")

    # run api client on our connection
    client = xbahn.shortcuts.api_client(connection)

    # instantiate widget using the client
    widget_a = DemoWidget(client, "widget_a")
    widget_a.set_number(123)
    print("Number on the server widget (A)", widget_a.get_number()) # 123

    # lets make another widget
    widget_b = DemoWidget(client, "widget_b")

    # since it's id 'widget_b' is different its not sharing the same
    # instance on the remote end as widget_a, meaning its number is unset
    print("Number on the server widget (B)", widget_b.get_number()) # 0

    # this one shares the same id as widget_a, meaning it will be 
    # connected to the same instance on the remote end
    widget_c = DemoWidget(client, "widget_a")
    print("Number on the server widget (C through A)", widget_c.get_number()) # 123

