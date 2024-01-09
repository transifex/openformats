import unittest
from openformats.formats.android_unescaped import AndroidUnescapedHandler
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string,
    strip_leading_spaces,
    bytes_to_string,
)

from openformats.strings import OpenString


class AndroidUnescapedTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidUnescapedHandler
    TESTFILE_BASE = "openformats/tests/formats/android/files"

    def setUp(self):
        super(AndroidUnescapedTestCase, self).setUp()
        self.handler = AndroidUnescapedHandler()

    def test_string(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement

        source_python_template = """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """
        source = source_python_template.format(key=random_key, string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(
            template, source_python_template.format(key=random_key, string=random_hash)
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_escape(self):
        rich = "&<>'\n\t@?" + '"'
        raw = "&amp;&lt;&gt;\\'\\n\\t\\@\\?" + '\\"'

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

    def test_unescape(self):
        rich = "&<>'\n\t@?" + '"'
        raw = "&amp;&lt;&gt;\\'\\n\\t\\@\\?" + '\\"'

        self.assertEqual(
            AndroidUnescapedHandler.unescape(raw),
            rich,
        )
