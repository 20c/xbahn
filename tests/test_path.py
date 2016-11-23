import unittest

import xbahn.path

class PathTestCase(unittest.TestCase):

    def test_append(self):

        self.assertEqual(xbahn.path.append("a","b","c"), "a.b.c")
        self.assertEqual(xbahn.path.append(".a.",".b","c."), "a.b.c")
        self.assertEqual(xbahn.path.append("a","b","","c"), "a.b.c")

    def test_split(self):

        self.assertEqual(xbahn.path.split("a.b.c"), ["a","b","c"])

    def test_walk(self):

        r = [a for a in xbahn.path.walk("a.b.c")]
        self.assertEqual(r, ["a", "a.b", "a.b.c"])

    def test_match(self):

        self.assertEqual(xbahn.path.match("a", "a.b.c"), True)
        self.assertEqual(xbahn.path.match("a.b", "a.b.c"), True)
        self.assertEqual(xbahn.path.match("a.b.c", "a.b.c"), True)

        self.assertEqual(xbahn.path.match("a.c", "a.b.c"), False)
        self.assertEqual(xbahn.path.match("a.b.d", "a.b.c"), False)
        self.assertEqual(xbahn.path.match("b", "a.b.c"), False)

    def test_tail(self):

        r = xbahn.path.tail("part.1", "part.1.part.2.part.3")
        self.assertEqual(r, ["part","2","part","3"])

        r = xbahn.path.tail("part.2", "part.1.part.2.part.3")
        self.assertEqual(r, [])
