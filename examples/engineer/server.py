import signal

import xbahn.api as api
import xbahn.engineer as engineer
import xbahn.connection.link as link
import xbahn.connection.zmq

from xbahn.connection import listen

class Server(api.Server):
    status = "ok"

    def do(self, what):
        return "did %s" % what


@Server.widget('engineer')
class Engineer(engineer.ServerWidget):
    @engineer.expose()
    def status(self):
        return self.comm.status

    @engineer.argument("what")
    @engineer.expose()
    def do_something(self, what):
        """
        Do the task specified in [WHAT]
        """
        return self.comm.do(what)

    @engineer.option("--extra/--no-extra", default=False, help="include extra info")
    @engineer.expose()
    def show(self, extra=False):
        rv = ["Basic"]
        if extra:
            rv.append("Extra!!")
        return rv

if __name__ == "__main__":
    conn = listen("zmq://0.0.0.0:7050/rep")
    lnk = link.Link()
    lnk.wire("main", receive=conn, respond=conn)
    server = Server(link=lnk)
    print("Server running ...")
    conn.wait_for_signal(signal.SIGINT)
