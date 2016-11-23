import pytest
from conftest import XbahnTestCase

class Base(object):
    class __TMPL__TestCase(XbahnTestCase):


class Test__TMPL__ZMQ(Base.__TMPL__TestCase):

    def setUp(self):
        self.setUpConnection(
            [("ZMQ_REP", 0)],
            [("ZMQ_REQ", 0)]
        )
