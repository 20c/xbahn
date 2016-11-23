import pytest
from conftest import XbahnTestCase

from click.testing import CliRunner

import xbahn.api as api
import xbahn.engineer as engineer
import xbahn.connection.link as link

class Server(api.Server):
    status = "ok"

@Server.widget("engineer")
class Engineer(engineer.ServerWidget):

    @engineer.expose()
    def status(self):
        return self.comm.status

    @engineer.expose()
    @engineer.argument("a", nargs=1)
    @engineer.argument("b", nargs=1)
    def multiply(self, a, b):
        """ take a number and multiply it with another number """
        return int(a) * int(b)

    @engineer.expose()
    @engineer.option("--extra/--no-extra", default=False, help="return extra information")
    def info(self, extra):
        if extra:
            return "status: ok, color: green"
        else:
            return "ok"


class Base(object):
    class EngineerTestCase(XbahnTestCase):

        def setUp(self):
            self.server_link = link.Link()
            self.server_link.wire(
                "main",
                receive=self.listeners[0],
                respond=self.listeners[0]
            )
            self.cli = CliRunner()
            self.host = self.listeners[0].remote.split("->")[1]

        def mimic_output(self, command, result):
            return "%s: %s> %s\n" % (self.host, command, result)

        def test_engineer(self):
            server = Server(link=self.server_link)


            # Test status command

            args = [self.host, "status"]
            r = self.cli.invoke(
                engineer.engineer, args
            )
            self.assertEqual(r.exit_code, 0)
            self.assertEqual(str(r.output), self.mimic_output("status", "ok"))

            # Test multiply command

            args = [self.host, "multiply", "5", "2"]
            r = self.cli.invoke(
                engineer.engineer, args
            )
            self.assertEqual(r.exit_code, 0)
            self.assertEqual(str(r.output), self.mimic_output("multiply", "10"))

            # Test info command (without --extra)

            args = [self.host, "info"]
            r = self.cli.invoke(
                engineer.engineer, args
            )
            self.assertEqual(r.exit_code, 0)
            self.assertEqual(str(r.output), self.mimic_output("info", "ok"))

            # Test info command (with --extra)

            args = [self.host, "info", "--extra"]
            r = self.cli.invoke(
                engineer.engineer, args
            )
            self.assertEqual(r.exit_code, 0)
            self.assertEqual(str(r.output), self.mimic_output("info", "status: ok, color: green"))

            # Test help

            args = [self.host, "multiply", "--help"]
            r = self.cli.invoke(
                engineer.engineer, args
            )
            self.assertEqual(r.exit_code, 0)

            expected = "\n".join([
                "Usage: engineer zmq://addr1/req?transport=inproc multiply [OPTIONS] B A",
                "",
                "  take a number and multiply it with another number",
                "",
                "Options:",
                "  --debug / --no-debug  Show debug information",
                "  --help                Show this message and exit.",
                ""
            ])

            self.assertEqual(r.output, expected)




class TestEngineerZMQ(Base.EngineerTestCase):

    def setUp(self):
        self.setUpConnections(
            [("REP", 0)],
            []
        )
        super(TestEngineerZMQ, self).setUp();
