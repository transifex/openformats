import unittest
from openformats.exceptions import ParseError
from openformats.formats.android_unescaped import AndroidUnescapedHandler
from openformats.tests.formats.android.test_android import AndroidTestCase
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
        rich = "< 20 units"
        raw = "&lt; 20 units"

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

        rich = "< 20 & > 50 units"
        raw = "&lt; 20 &amp; &gt; 50 units"

        self.assertEqual(
            AndroidUnescapedHandler.escape(rich),
            raw,
        )

        rich = "< 20 & > 50 units<xliff:g>test</xliff:g>"
        raw = "&lt; 20 &amp; &gt; 50 units&lt;xliff:g&gt;test&lt;/xliff:g&gt;"

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

    # New tests for CDATA functionality
    def test_process_with_cdata_preservation_no_cdata(self):
        """Test _process_with_cdata_preservation with text that has no CDATA sections."""

        def dummy_process(text):
            return text.replace("&", "&amp;")

        text = "Hello & world"
        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            text, dummy_process, is_escape=True
        )
        self.assertEqual(result, "Hello &amp; world")

    def test_process_with_cdata_preservation_empty_text(self):
        """Test _process_with_cdata_preservation with empty or None text."""

        def dummy_process(text):
            if text is None:
                return None
            return text.replace("&", "&amp;")

        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            "", dummy_process, is_escape=True
        )
        self.assertEqual(result, "")

        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            None, dummy_process, is_escape=True
        )
        self.assertEqual(result, None)

    def test_process_with_cdata_preservation_single_cdata(self):
        """Test _process_with_cdata_preservation with a single CDATA section."""

        def dummy_process(text):
            return text.replace("&", "&amp;")

        text = "Before <![CDATA[& raw content ']]> after"
        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            text, dummy_process, is_escape=True
        )
        # The & in regular text should be escaped, but CDATA content is only processed for quotes
        expected = "Before <![CDATA[& raw content \\']]> after"
        self.assertEqual(result, expected)

    def test_process_with_cdata_preservation_multiple_cdata(self):
        """Test _process_with_cdata_preservation with multiple CDATA sections."""

        def dummy_process(text):
            return text.replace("&", "&amp;")

        text = "Start & <![CDATA[first 'section']]> middle & <![CDATA[second \"section\"]]> end &"
        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            text, dummy_process, is_escape=True
        )
        expected = "Start &amp; <![CDATA[first \\'section\\']]> middle &amp; <![CDATA[second \\\"section\\\"]]> end &amp;"
        self.assertEqual(result, expected)

    def test_process_with_cdata_preservation_unescape(self):
        """Test _process_with_cdata_preservation with unescaping."""

        def dummy_process(text):
            return text.replace("&amp;", "&")

        text = "Before &amp; <![CDATA[\\'raw\\' content]]> after &amp;"
        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            text, dummy_process, is_escape=False
        )
        expected = "Before & <![CDATA['raw' content]]> after &"
        self.assertEqual(result, expected)

    def test_process_with_cdata_preservation_multiline_cdata(self):
        """Test _process_with_cdata_preservation with multiline CDATA content."""

        def dummy_process(text):
            return text.replace("&", "&amp;")

        text = """Before & <![CDATA[
        multiline
        content with \'quotes\'
        ]]> after &"""
        result = AndroidUnescapedHandler._process_with_cdata_preservation(
            text, dummy_process, is_escape=True
        )
        expected = """Before &amp; <![CDATA[
        multiline
        content with \\\'quotes\\\'
        ]]> after &amp;"""
        self.assertEqual(result, expected)

    def test_escape_with_cdata_simple(self):
        """Test escape method with simple CDATA content."""
        text = "Hello & <![CDATA[raw 'content']]> world &"
        result = AndroidUnescapedHandler.escape(text)
        expected = "Hello &amp; <![CDATA[raw \\'content\\']]> world &amp;"
        self.assertEqual(result, expected)

    def test_escape_with_cdata_complex(self):
        """Test escape method with complex CDATA content including various characters."""
        text = "Start @ <![CDATA[<b>Bold</b> with \"quotes\" and 'apostrophes']]> end ?"
        result = AndroidUnescapedHandler.escape(text)
        expected = "Start \\@ <![CDATA[<b>Bold</b> with \\\"quotes\\\" and \\'apostrophes\\']]> end \\?"
        self.assertEqual(result, expected)

    def test_escape_with_cdata_and_inline_tags(self):
        """Test escape method with CDATA sections alongside inline tags."""
        text = (
            "Text <xliff:g id=\"1\">%1$s</xliff:g> & <![CDATA[raw 'data']]> more text"
        )
        result = AndroidUnescapedHandler.escape(text)
        expected = "Text <xliff:g id=\"1\">%1$s</xliff:g> &amp; <![CDATA[raw \\'data\\']]> more text"
        self.assertEqual(result, expected)

    def test_unescape_with_cdata_simple(self):
        """Test unescape method with simple CDATA content."""
        text = "Hello &amp; <![CDATA[raw \\'content\\']]> world &amp;"
        result = AndroidUnescapedHandler.unescape(text)
        expected = "Hello & <![CDATA[raw 'content']]> world &"
        self.assertEqual(result, expected)

    def test_unescape_with_cdata_complex(self):
        """Test unescape method with complex CDATA content."""
        text = "Start \\@ <![CDATA[<b>Bold</b> with \\\"quotes\\\" and \\'apostrophes\\']]> end \\?"
        result = AndroidUnescapedHandler.unescape(text)
        expected = (
            "Start @ <![CDATA[<b>Bold</b> with \"quotes\" and 'apostrophes']]> end ?"
        )
        self.assertEqual(result, expected)

    def test_escape_unescape_cdata_roundtrip(self):
        """Test that escape and unescape are symmetric for CDATA content."""
        original = (
            "Text & <![CDATA[Raw content with \"quotes\" and 'apostrophes']]> @ ?"
        )
        escaped = AndroidUnescapedHandler.escape(original)
        unescaped = AndroidUnescapedHandler.unescape(escaped)
        self.assertEqual(original, unescaped)

    def test_cdata_with_nested_brackets(self):
        """Test CDATA sections containing nested brackets."""
        text = "Before <![CDATA[Some [nested] content]]> after"
        escaped = AndroidUnescapedHandler.escape(text)
        unescaped = AndroidUnescapedHandler.unescape(escaped)
        self.assertEqual(text, unescaped)

    def test_cdata_empty_content(self):
        """Test CDATA sections with empty content."""
        text = "Before <![CDATA[]]> after &"
        result = AndroidUnescapedHandler.escape(text)
        expected = "Before <![CDATA[]]> after &amp;"
        self.assertEqual(result, expected)

    def test_cdata_only_quotes(self):
        """Test CDATA sections containing only quotes."""
        text = "Before <![CDATA['\"]]> after"
        escaped = AndroidUnescapedHandler.escape(text)
        expected = "Before <![CDATA[\\'\\\"]]> after"
        self.assertEqual(escaped, expected)

        unescaped = AndroidUnescapedHandler.unescape(escaped)
        self.assertEqual(text, unescaped)

    def test_adjacent_cdata_sections(self):
        """Test adjacent CDATA sections."""
        text = "<![CDATA[first 'section']]><![CDATA[second \"section\"]]>"
        escaped = AndroidUnescapedHandler.escape(text)
        expected = "<![CDATA[first \\'section\\']]><![CDATA[second \\\"section\\\"]]>"
        self.assertEqual(escaped, expected)

        unescaped = AndroidUnescapedHandler.unescape(escaped)
        self.assertEqual(text, unescaped)

    def test_cdata_at_boundaries(self):
        """Test CDATA sections at text boundaries."""
        # CDATA at start
        text = "<![CDATA[start 'content']]> regular text &"
        escaped = AndroidUnescapedHandler.escape(text)
        expected = "<![CDATA[start \\'content\\']]> regular text &amp;"
        self.assertEqual(escaped, expected)

        # CDATA at end
        text = "regular text & <![CDATA[end 'content']]>"
        escaped = AndroidUnescapedHandler.escape(text)
        expected = "regular text &amp; <![CDATA[end \\'content\\']]>"
        self.assertEqual(escaped, expected)

    def test_malformed_cdata_like_text(self):
        """Test text that looks like CDATA but isn't properly formed."""
        # Missing closing bracket
        text = "Before <![CDATA[content] after &"
        result = AndroidUnescapedHandler.escape(text)
        # Should be treated as regular text since it's not valid CDATA
        expected = "Before &lt;![CDATA[content] after &amp;"
        self.assertEqual(result, expected)

        # Missing opening bracket
        text = "Before ![CDATA[content]]> after &"
        result = AndroidUnescapedHandler.escape(text)
        expected = "Before ![CDATA[content]]&gt; after &amp;"
        self.assertEqual(result, expected)

    def test_cdata_with_special_android_chars(self):
        """Test CDATA preservation with Android-specific special characters."""
        text = (
            "Before & <![CDATA[@string/test_ref and \\n newline and \\t tab]]> after @"
        )
        escaped = AndroidUnescapedHandler.escape(text)
        expected = "Before &amp; <![CDATA[@string/test_ref and \\n newline and \\t tab]]> after \\@"
        self.assertEqual(escaped, expected)

        unescaped = AndroidUnescapedHandler.unescape(escaped)
        self.assertEqual(text, unescaped)
