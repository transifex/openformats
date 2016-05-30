import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.po import PoHandler


class PoTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = PoHandler
    TESTFILE_BASE = "openformats/tests/formats/po/files"

    def setUp(self):
        super(PoTestCase, self).setUp()
        self.handler = PoHandler()

    def test_empty_msgid(self):
        self._test_parse_error(
            u"""
            msgid ""
            msgstr ""

            msgid ""
            msgstr "Not a plural"
            """,
            u"Found empty msgid"
        )

    def test_incomplete_plurals(self):
        self._test_parse_error(
            u"""
                msgid ""
                msgstr ""

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "Not a plural"
                msgstr[1] ""
            """,
            u"Incomplete plurals found on string with msgid `p1` "
            u"and msgid_plural `p2`"
        )
