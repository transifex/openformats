import unittest

from openformats.tests.formats.common import CommonFormatTestCase
from openformats.formats.plaintext import PlaintextHandler


class PlaintextTestCase(CommonFormatTestCase, unittest.TestCase):
    HANDLER_CLASS = PlaintextHandler
    TESTFILE_BASE = "openformats/tests/formats/plaintext/files"
