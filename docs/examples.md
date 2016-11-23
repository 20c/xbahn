# API

A few examples to get you started with the xbahn API, using zmq as a handler.

All examples were tested with python 3.4

## One way communication

It should be noted, when i refer to one-way communication here i am talking about
who can initiate requests, not whether or not the second party is able to respond to the request of the first.

In other words, one way communication allows you to implement a simple request -> reply line of comminucation where the second party (in this case the server) is only allows to communicate to the first party (in this case the client) through responses to requests made by the first party..

### Server

```py
{!examples/api/one_way/server.py!}
```
### Client

```py
{!examples/api/one_way/client.py!}
```

## Two way comminucation

Two way comminucation means both parties may initiate requests to each other. Once the client connects to the server, the server will automatically establish a connection to the client responder, to allow it to initiate requests to the client as well.

### Server

```py
{!examples/api/two_way/server.py!}
```
### Client

```py
{!examples/api/two_way/client.py!}
```

# API Widgets

API Widgets are a modular way to attach functionality to an api communicator (client or server)

## Unaware Server

A normal api server will have common widget instances shared by all clients

### Server

```py
{!examples/api/widget/server.py!}
```
### Client

```py
{!examples/api/widget/client.py!}
```

## Widget Aware Server

A widget-aware server groups widgets by client connection, meaning each client only has access
to the widgets it spawns.

Additionally, it also allows for the server to call functions on the client side widget (similar to API two-way communication example)

### Server

```py
{!examples/api/widget_aware_server/server.py!}
```
### Client

```py
{!examples/api/widget_aware_server/client.py!}
```

# Engineer

Engineer is a cli built upon click and xbahn, it allows you to call xbahn expose functions via a command line interface.

In order to expose api functionality to engineer the Widget system is used. Here is a quick and dirty example.

```py
{!examples/engineer/server.py!}
```

## Usage

Passing --help without any other options or arguments

```
engineer --help
```

```
Usage: engineer [OPTIONS] HOST COMMAND [ARGS]...

  run an engineer exposed action on a remote xbahn host

Options:
  --version             Show the version and exit.
  --debug / --no-debug  Show debug information
  --help                Show this message and exit.

Commands:
  shell  open an engineer shell
```

Passing --help with the host argument will show you what commands the server will accept

```
engineer zmq://0.0.0.0:7050/req --help
```

```
Usage: engineer [OPTIONS] HOST COMMAND [ARGS]...

  run an engineer exposed action on a remote xbahn host

Options:
  --version             Show the version and exit.
  --debug / --no-debug  Show debug information
  --help                Show this message and exit.

Commands:
  do_something  Do the task specified in [WHAT]
  show
  status
  shell         open an engineer shell
```

Calling the do_something command

```
engineer zmq://0.0.0.0:7050/req do_something "say hello"
zmq://0.0.0.0:7050/req: do_something> did say hello
```
