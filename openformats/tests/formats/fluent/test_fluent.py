import unittest

from openformats.formats.fluent import FluentHandler
from openformats.strings import OpenString


class FluentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = FluentHandler()

    def test_simple(self):
        template, stringset = self.handler.parse("a = b")
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "b")
        self.assertEqual(string.order, 0)
        self.assertEqual(template, f"a = {string.template_replacement}")

        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, "a = b")

        compiled = self.handler.compile(template, [OpenString("a", "bbb", order=0)])
        self.assertEqual(compiled, "a = bbb")

    def test_multiline(self):
        source = "\n".join(["a = b", "  c", "  d"])
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "\n".join(["b", "  c", "  d"]))
        self.assertEqual(string.order, 0)
        self.assertEqual(template, f"a = {string.template_replacement}")
        self.assertEqual(FluentHandler.unescape(string.string), "b c d")

        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_attributes(self):
        source = "\n".join(["a = b", "  .c = d"])
        template, stringset = self.handler.parse(source)
        self.assertEqual(stringset[0].key, "a")
        self.assertEqual(stringset[0].string, "b")
        self.assertEqual(stringset[0].order, 0)
        self.assertEqual(stringset[1].key, "a.c")
        self.assertEqual(stringset[1].string, "d")
        self.assertEqual(stringset[1].order, 1)
        self.assertEqual(
            template,
            "\n".join(
                [
                    "a = {}".format(stringset[0].template_replacement),
                    "  .c = {}".format(stringset[1].template_replacement),
                ]
            ),
        )
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_skip_message(self):
        template, stringset = self.handler.parse("\n".join(["a = b", "c = d"]))

        compiled = self.handler.compile(template, stringset[1:])
        self.assertEqual(compiled.strip(), "c = d")
        compiled = self.handler.compile(template, stringset[:1])
        self.assertEqual(compiled.strip(), "a = b")

    def test_skip_message_with_attributes(self):
        template, stringset = self.handler.parse(
            "\n".join(["a = b", "  .c = d", "e = f"])
        )

        compiled = self.handler.compile(template, stringset[1:])
        self.assertEqual(compiled.strip(), "e = f")

    def test_skip_attribute(self):
        template, stringset = self.handler.parse(
            "\n".join(["a = b", "  .c = d", "  .e = f"])
        )

        compiled = self.handler.compile(template, stringset[:2])
        self.assertEqual(compiled.strip(), "\n".join(["a = b", "  .c = d"]))

        compiled = self.handler.compile(template, stringset[::2])
        self.assertEqual(
            [line for line in compiled.splitlines() if not line.isspace()],
            ["a = b", "  .e = f"],
        )
