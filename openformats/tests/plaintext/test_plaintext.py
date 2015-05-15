import unittest
from openformats.tests.common import CommonFormatTestCase
from openformats.formats.plaintext import PlaintextHandler


class PlaintextTestCase(CommonFormatTestCase, unittest.TestCase):
    FORMAT_EXTENSION = "txt"
    HANDLER_CLASS = PlaintextHandler
    TESTFILE_BASE = "openformats/tests/plaintext/files"
