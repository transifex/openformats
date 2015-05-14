import unittest
from openformats.tests.common import CommonFormatTestCase
from openformats.formats.plaintext import PlaintextHandler


class PlaintextTestCase(CommonFormatTestCase, unittest.TestCase):
    HANDLER_CLASS = PlaintextHandler
    TESTFILE_BASE = "openformats/tests/plaintext/files"
