import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.po import PoHandler


class PoTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = PoHandler
    TESTFILE_BASE = "openformats/tests/formats/po/files"

    def setUp(self):
        super(PoTestCase, self).setUp()
        self.handler = PoHandler()
