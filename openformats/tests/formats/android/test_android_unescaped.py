import unittest
from openformats.exceptions import ParseError
from openformats.formats.android_unescaped import AndroidUnescapedHandler
from openformats.formats.android_v3 import AndroidHandlerv3
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
        self.maxDiff = None
        random_key = generate_random_string()
        uploaded_string = """&amp; &lt; &gt; \\' \\n \\t \\@ \\? \\" <xliff:g id="1">%1$s</xliff:g> \@ \?"""
        uploaded_openstring = OpenString(random_key, uploaded_string, order=0)
        uploaded_hash = uploaded_openstring.template_replacement

        source_python_template = """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """
        source = source_python_template.format(key=random_key, string=uploaded_string)
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [uploaded_openstring])

        self.assertEqual(
            template,
            source_python_template.format(key=random_key, string=uploaded_hash),
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, uploaded_openstring.__dict__)
        self.assertEqual(compiled, source)



    def test_escape(self):
        rich = '&>"\n\t@? <xliff:g id="1">%1$s &</xliff:g> @ ?'
        raw = '&amp;&gt;\\"\\n\\t\\@\\? <xliff:g id="1">%1$s &</xliff:g> \\@ \\?'

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

    def test_escape_lt_character(self):
        rich = '< 20 units'
        raw = '&lt; 20 units'

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

        rich = '< 20 & > 50 units'
        raw = '&lt; 20 &amp; &gt; 50 units'

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

        rich = '< 20 & > 50 units<xliff:g>test</xliff:g>'
        raw = '&lt; 20 &amp; &gt; 50 units&lt;xliff:g&gt;test&lt;/xliff:g&gt;'

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

    def test_create_string_raises_error(self):
        unescaped_string = "some ' string"
        self.assertRaises(
            ParseError,
            AndroidUnescapedHandler._check_unescaped_characters,
            unescaped_string,
        )
        unescaped_string = 'some " string'
        self.assertRaises(
            ParseError,
            AndroidUnescapedHandler._check_unescaped_characters,
            unescaped_string,
        )

