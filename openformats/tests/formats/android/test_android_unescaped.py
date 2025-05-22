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

    # def setUp(self):
    #     super(AndroidUnescapedTestCase, self).setUp()
    #     self.handler = AndroidUnescapedHandler()

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


    # def test_cdata_string_plurals(self):
    #     self.maxDiff = None
    #     uploaded_openstring = OpenString("first_string", "non plural cdata", order=0)
    #     uploaded_openstring2 = OpenString("second_string", "no plural signle", order=1)
    #     uploaded_openstring3 = OpenString("third_string", {1: "plural one", 5: "plural other"}, order=2)
    #     uploaded_hash = uploaded_openstring.template_replacement
    #     uploaded_hash2 = uploaded_openstring2.template_replacement
    #     uploaded_hash3 = uploaded_openstring3.template_replacement

    #     source= """
    #         <resources>
    #             <string name="first_string">
    #                 <![CDATA[non plural cdata]]>
    #             </string>
    #             <string name="second_string">no plural signle</string>

    #             -----
    #             <plurals name="third_string">
    #                 <item quantity="one">
    #                     <![CDATA[plural one]]>
    #                 </item>
    #                 <item quantity="other">
    #                     <![CDATA[plural other]]>
    #                 </item>
    #             </plurals>
    #         </resources>
    #     """
    #     cdata_source_python_template = f"""
    #         <resources>
                
    #             <string name="{uploaded_openstring3.key}">{uploaded_hash3}</string>
    #         </resources>
    #     """

    #     template, stringset = self.handler.parse(source)
    #     from icecream import ic
      
    #     compiled = self.handler.compile(template, [uploaded_openstring3])
    #     ic(compiled)
    #     return
    #     self.assertEqual(
    #         template,
    #         cdata_source_python_template,
    #     )
    #     self.assertEqual(len(stringset), 3)
    #     self.assertEqual(stringset[0].__dict__, uploaded_openstring.__dict__)
    #     self.assertEqual(compiled, source)
    #     self.assertEqual(self.handler.debug_counter, 3)

    def test_cdata_string(self):
        self.maxDiff = None
        uploaded_openstring = OpenString("onshape_edu_plan", "<b>Onshape Education Plan</b>", order=0)
        uploaded_openstring2 = OpenString("explore_the_basics", "Explore the basics", order=1)
        uploaded_openstring3 = OpenString("test", "<b>Onshape Education Plan</b>", order=2)
        uploaded_hash = uploaded_openstring.template_replacement
        uploaded_hash2 = uploaded_openstring2.template_replacement
        uploaded_hash3 = uploaded_openstring3.template_replacement

        source= """
            <resources>
                <string name="onshape_edu_plan"><![CDATA[<b>Onshape Education Plan</b>]]></string>
                <string name="explore_the_basics">Explore the basics</string>
                <string name="test"><b>Onshape Education Plan</b></string>
            </resources>
        """
        cdata_source_python_template = f"""
            <resources>
                <string name="{uploaded_openstring.key}"><![CDATA[{uploaded_hash}]]></string>
                <string name="{uploaded_openstring2.key}">{uploaded_hash2}</string>
                <string name="{uploaded_openstring3.key}">{uploaded_hash3}</string>
            </resources>
        """

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [uploaded_openstring,uploaded_openstring2,uploaded_openstring3])
        self.assertEqual(
            template,
            cdata_source_python_template,
        )
        self.assertEqual(len(stringset), 3)
        self.assertEqual(stringset[0].__dict__, uploaded_openstring.__dict__)
        self.assertEqual(compiled, source)
        self.assertEqual(self.handler.debug_counter, 3)


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
