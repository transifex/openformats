import unittest
from openformats.tests.common import CommonFormatTestCase
from openformats.formats.srt import SrtHandler


class SrtTestCase(CommonFormatTestCase, unittest.TestCase):
    FORMAT_EXTENSION = "srt"
    HANDLER_CLASS = SrtHandler
    TESTFILE_BASE = "openformats/tests/srt/files"
