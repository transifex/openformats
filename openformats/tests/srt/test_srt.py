import unittest
from openformats.tests.common import CommonFormatTestCase
from openformats.formats.srt import SrtHandler


class SrtTestCase(CommonFormatTestCase, unittest.TestCase):
    FORMAT_EXTENSION = "srt"
    HANDLER_CLASS = SrtHandler
    TESTFILE_BASE = "openformats/tests/srt/files"

    def test_srt_occurrences(self):
        """srt: Test that timings are saved as occurrencies."""
        template, stringset = self.handler.parse(self.data["1_en"])
        self.assertEqual(stringset[0].occurrences, '00:01:28.797,00:01:30.297')
