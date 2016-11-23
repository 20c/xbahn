"""
xbahn engineer is a cli that allows you to query and execute remote xbahn endpoints
in a managed manner.
"""

from __future__ import print_function
import logging
import click
import code
import xbahn.api as api
import xbahn.connection.link as link

from xbahn.connection import connect

from xbahn.mixins import EventMixin

def setup_debug_logging():
    """
    set up debug logging
    """

    logger = logging.getLogger("xbahn")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    logger.addHandler(ch)

class doc(object):

    """
    decorator that lets you change docstring of
    a function.

    needed to pass a dynamic docstring to
    click decorated remote xbahn api functions
    """

    def __init__(self, text):
        self.text = text

    def __call__(self, fn):
        fn.__doc__ = self.text
        return fn

class EngineerDecorator(object):

    """
    Base class for engineer decorators
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):
        if not hasattr(fn, "engineer"):
            fn.engineer = {
                "description" : "",
                "arguments" : [],
                "options" : []
            }
        return fn


class expose(EngineerDecorator):

    """
    Decorator to expose a function to engineer

    Calls api.expose automatically
    """

    def __call__(self, fn):
        fn = api.expose(super(expose, self).__call__(fn))
        fn.engineer["description"] = fn.__doc__
        return fn


class argument(EngineerDecorator):

    """
    Decorator to describe an argument for an exposed
    engineer api endpoint (mimics @click.argument)
    """

    def __call__(self, fn):
        fn = super(argument, self).__call__(fn)
        fn.engineer["arguments"].append({"args":self.args,"kwargs":self.kwargs})
        return fn


class option(EngineerDecorator):

    """
    Decorator to describe an option for an exposed
    engineer api endpoint (mimics @click.option)
    """

    def __call__(self, fn):
        fn = super(option, self).__call__(fn)
        fn.engineer["options"].append({"args":self.args,"kwargs":self.kwargs})
        return fn


class ServerWidget(api.Widget):

    """
    Base Engineer server-side widget
    """

    @api.expose
    def engineer_list_commands(self):

        """
        Returns a list of all api end points (commands) exposed
        to engineer
        """

        rv = []
        for k in dir(self):
            attr = getattr(self,k)
            if type(getattr(attr, "engineer", None)) == dict:
                rv.append(k)
        return rv

    @api.expose
    def engineer_info(self, action):

        """
        Returns:
            dict: engineer command information
                - arguments (list<dict>): command arguments
                    - args (list):  args to pass through to click.argument
                    - kwargs (dict): keyword arguments to pass through to click.argument
                - options (list<dict>): command options
                    - args (list):  args to pass through to click.option
                    - kwargs (dict): keyword options to pass through to click.option
        """

        fn = getattr(self, action, None)
        if not fn:
            raise AttributeError("Engineer action not found: %s" % action)
        if not hasattr(fn, "engineer"):
            raise AttributeError("Engineer action not exposed: %s" % action)

        return fn.engineer


@api.Client.widget('engineer')
class ClientWidget(api.Widget):
    pass

class Engineer(click.Group):

    """
    Extended click group that allows to fetch command information
    from remote xbahn.api endpoint
    """

    def connect(self, ctx):

        """
        establish xbahn connection and store on click context
        """

        if hasattr(ctx,"conn") or "host" not in ctx.params:
            return

        ctx.conn = conn = connect(ctx.params["host"])
        lnk = link.Link()
        lnk.wire("main", receive=conn, send=conn)
        ctx.client = api.Client(link=lnk)
        ctx.widget = ClientWidget(ctx.client, "engineer")


    def list_commands(self, ctx):

        """
        list all commands exposed to engineer
        """


        self.connect(ctx)

        if not hasattr(ctx, "widget"):
            return super(Engineer, self).list_commands(ctx)

        return ctx.widget.engineer_list_commands() + super(Engineer, self).list_commands(ctx)

    def get_command(self, ctx, name):

        """
        get click command from engineer exposed xbahn command specs
        """

        # connect to xbahn
        self.connect(ctx)

        if not hasattr(ctx, "widget") or name in ["shell"]:
            return super(Engineer, self).get_command(ctx, name)

        if name == "--help":
            return None

        # get the command specs (description, arguments and options)
        info = ctx.widget.engineer_info(name)

        # make command from specs
        return self.make_command(ctx, name, info)

    def make_command(self, ctx, name, info):

        """
        make click sub-command from command info
        gotten from xbahn engineer
        """

        @self.command()
        @click.option("--debug/--no-debug", default=False, help="Show debug information")
        @doc(info.get("description"))
        def func(*args, **kwargs):
            if "debug" in kwargs:
                del kwargs["debug"]
            fn = getattr(ctx.widget, name)
            result = fn(*args, **kwargs)
            click.echo("%s: %s> %s" % (ctx.params["host"],name,result))
            ctx.conn.close()

        ctx.info_name = "%s %s" % (ctx.info_name , ctx.params["host"])

        for a in info.get("arguments",[]):
            deco = click.argument(*a["args"], **a["kwargs"])
            func = deco(func)
        for o in info.get("options",[]):
            deco = click.option(*o["args"], **o["kwargs"])
            func = deco(func)

        return func



@click.group(cls=Engineer)
@click.pass_context
@click.version_option()
@click.argument("host", nargs=1)
@click.option("--debug/--no-debug", default=False, help="Show debug information")
def engineer(ctx, host, debug):
    """
    run an engineer exposed action on a remote xbahn host
    """
    return

@engineer.command()
@click.pass_context
def shell(ctx):
    """
    open an engineer shell
    """

    shell = code.InteractiveConsole({"engineer": getattr(ctx.parent, "widget", None)})
    shell.interact("\n".join([
        "Engineer connected to %s" % ctx.parent.params["host"],
        "Dispatch available through the 'engineer' object"
    ]))

if __name__ == "__main__":
    engineer()
    ctx = click.get_current_context()
    if hasattr(ctx, "conn"):
        ctx.conn.close()
