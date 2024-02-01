import unittest
from openformats.formats.android_unescaped import AndroidUnescapedHandler
from openformats.tests.formats.android.test_android import AndroidTestCase
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string,
    strip_leading_spaces,
    bytes_to_string,
)

from openformats.strings import OpenString


class AndroidUnescapedFromAndroidTestCase(AndroidTestCase):
    HANDLER_CLASS = AndroidUnescapedHandler
    TESTFILE_BASE = "openformats/tests/formats/android/files"

    def setUp(self):
        super(AndroidUnescapedFromAndroidTestCase, self).setUp()
        self.handler = AndroidUnescapedHandler()


class AndroidUnescapedTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidUnescapedHandler
    TESTFILE_BASE = "openformats/tests/formats/android/files"

    def setUp(self):
        super(AndroidUnescapedTestCase, self).setUp()
        self.handler = AndroidUnescapedHandler()

    def test_string(self):
        self.maxDiff = None
        random_key = generate_random_string()
        uploaded_string = (
            '&amp; &lt; &gt; \' \n \t \@ \? " <xliff:g id="1">%1$s</xliff:g>'
        )
        stored_string = (
            '&amp; &lt; &gt; \\\' \n \t \@ \? \\" <xliff:g id="1">%1$s</xliff:g>'
        )
        stored_openstring = OpenString(random_key, stored_string, order=0)
        random_hash = stored_openstring.template_replacement

        source_python_template = """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """
        source = source_python_template.format(key=random_key, string=uploaded_string)
        stored_source = source_python_template.format(
            key=random_key, string=stored_string
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [stored_openstring])

        self.assertEqual(
            template, source_python_template.format(key=random_key, string=random_hash)
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, stored_openstring.__dict__)
        self.assertEqual(compiled, stored_source)

    def test_escape(self):
        rich = '&>"\n\t@? <xliff:g id="1">%1$s &</xliff:g>'
        raw = '&amp;&gt;\\"\\n\\t\\@\\? <xliff:g id="1">%1$s &</xliff:g>'

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
