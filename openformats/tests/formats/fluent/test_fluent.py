import unittest

from openformats.formats.fluent import FluentHandler
from openformats.strings import OpenString


class FluentTestCase(unittest.TestCase):
    def test_simple(self):
        h = FluentHandler()
        template, stringset = h.parse("a = b")
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "b")
        self.assertEqual(string.order, 0)
        self.assertEqual(template, f"a = {string.template_replacement}")

        compiled = h.compile(template, stringset)
        self.assertEqual(compiled, "a = b")

        compiled = h.compile(template, [OpenString("a", "bbb", order=0)])
        self.assertEqual(compiled, "a = bbb")

    def test_multiline(self):
        source = "\n".join(["a = b", "  c", "  d"])
        h = FluentHandler()
        template, stringset = h.parse(source)
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "\n".join(["b", "  c", "  d"]))
        self.assertEqual(string.order, 0)
        self.assertEqual(template, f"a = {string.template_replacement}")
        self.assertEqual(FluentHandler.unescape(string.string), "b c d")

        compiled = h.compile(template, stringset)
        self.assertEqual(compiled, source)
