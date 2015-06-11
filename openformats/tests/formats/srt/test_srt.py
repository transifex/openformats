import unittest

from openformats.tests.formats.common import CommonFormatTestCase
from openformats.tests.utils import strip_leading_spaces
from openformats.formats.srt import SrtHandler


class SrtTestCase(CommonFormatTestCase, unittest.TestCase):
    HANDLER_CLASS = SrtHandler
    TESTFILE_BASE = "openformats/tests/formats/srt/files"

    def test_srt_occurrences(self):
        """srt: Test that timings are saved as occurrencies."""
        source = strip_leading_spaces("""
            1
            00:01:28,797 --> 00:01:30,297
            Hello, World!
        """)
        template, stringset = self.handler.parse(source)
        self.assertEqual(stringset[0].occurrences, '00:01:28.797,00:01:30.297')

    def test_missing_order(self):
        source = strip_leading_spaces("""
            00:01:28,797 --> 00:01:30,297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Order number on line 1 (00:01:28,797 --> 00:01:30,297) must be a "
            "positive integer"
        )

    def test_missing_timings(self):
        source = strip_leading_spaces("""
            1
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Timings on line 2 don't follow '[start] --> [end] (position)' "
            "pattern"
        )

    def test_missing_string(self):
        source = strip_leading_spaces("""
            1
            00:01:28,797 --> 00:01:30,297
        """)
        template, stringset = self.handler.parse(source)
        self.assertEquals(template, source)
        self.assertEquals(len(stringset), 0)

    def test_negative_order(self):
        source = strip_leading_spaces("""
            -3
            00:01:28,797 --> 00:01:30,297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Order number on line 1 (-3) must be a positive integer"
        )

    def test_non_ascending_order(self):
        source = strip_leading_spaces("""
            2
            00:01:28,797 --> 00:01:30,297
            Hello, World!

            1
            00:04:28,797 --> 00:08:30,297
            Goodbye, World!
        """)
        self._test_parse_error(
            source,
            "Order numbers must be in ascending order; number in line 5 (1) "
            "is wrong"
        )

    def test_wrong_timings(self):
        source = strip_leading_spaces("""
            1
            00:01:28,797 00:01:30,297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Timings on line 2 don't follow '[start] --> [end] (position)' "
            "pattern"
        )

        source = strip_leading_spaces("""
            1
            00:fas28,797 --> 00:01:30,297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Problem with start of timing at line 2: '00:fas28,797'"
        )

        source = strip_leading_spaces("""
            1
            00:01:28,797 --> 00:ois30,297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Problem with end of timing at line 2: '00:ois30,297'"
        )
