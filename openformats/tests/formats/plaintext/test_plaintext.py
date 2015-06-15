import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.plaintext import PlaintextHandler


class PlaintextTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = PlaintextHandler
    TESTFILE_BASE = "openformats/tests/formats/plaintext/files"
