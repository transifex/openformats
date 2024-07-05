import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils import strip_leading_spaces
from openformats.formats.vtt import VttHandler


class VttTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = VttHandler
    TESTFILE_BASE = "openformats/tests/formats/vtt/files"

    def test_vtt_metadata(self):
        """vtt: Test that metadata is included in template but not included in stringset."""
        source = strip_leading_spaces("""WEBVTT

            STYLE
            ::cue(v) {
            color: red;
            }

            REGION
            id:fred
            width:40%

            1
            00:01:28.797 --> 00:01:30.297
            Hello, World!

            NOTE want this test to pass
        """)
        template, stringset = self.handler.parse(source)
        for str in stringset:
            s = str.string
            self.assertFalse('WEBVTT' in s or 'STYLE' in s or 'REGION' in s or 'NOTE' in s,
                             'Metadata should not be present in stringset!')
            break
        self.assertIn('WEBVTT', template)
        self.assertIn('STYLE', template)
        self.assertIn('REGION', template)
        self.assertIn('NOTE', template)

        source = strip_leading_spaces("""
            00:01:28.797 --> 00:01:30.297
            Check the first line
        """)
        self._test_parse_error(source, "VTT file should start with 'WEBVTT'!")

    def test_vtt_occurrences(self):
        """vtt: Test that timings are saved as occurrencies."""
        source = strip_leading_spaces("""WEBVTT

            1
            00:01:28.797 --> 00:01:30.297
            Hello, World!
        """)
        _, stringset = self.handler.parse(source)
        self.assertEqual(stringset[0].occurrences, '00:01:28.797,00:01:30.297')

    def test_missing_string(self):
        source = strip_leading_spaces("""WEBVTT

            1
            00:01:28.797 --> 00:01:30.297
        """)
        template, _ = self.handler.parse(source)
        self.assertEqual(source, template)

    def test_full_and_short_timings(self):
        source = strip_leading_spaces("""WEBVTT

            00:01:28.797 --> 00:01:30.297
            Full timings hh:mm:ss.fff

            01:28.797 --> 01:30.297
            Short timings mm:ss.fff

            28.797 --> 30.297
            Abnormal timings format ss.fff
        """)
        self._test_parse_error(
            source,
            "Unexpected timing format on line 11"
        )

    def test_wrong_timings(self):
        source = strip_leading_spaces("""WEBVTT

            1
            00:01:28.797 ---> 00:01:30.297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Timings on line 4 don't follow '[start] --> [end] (position)' "
            "pattern"
        )

        source = strip_leading_spaces("""WEBVTT

            1
            00:fas28.797 --> 00:01:30.297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Problem with start of timing at line 4: '00:fas28.797'"
        )

        source = strip_leading_spaces("""WEBVTT

            1
            00:01:28.797 --> 00:ois30.297
            Hello, World!
        """)
        self._test_parse_error(
            source,
            "Problem with end of timing at line 4: '00:ois30.297'"
        )
