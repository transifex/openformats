import unittest
from openformats.exceptions import ParseError
from openformats.formats.android_v3 import AndroidHandlerv3
from openformats.tests.formats.common import CommonFormatTestMixin

from openformats.strings import OpenString


class AndroidHandler3TestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidHandlerv3
    TESTFILE_BASE = "openformats/tests/formats/android/files"
    def setUp(self):
        super(AndroidHandler3TestCase, self).setUp()
        self.handler = AndroidHandlerv3()
    
    def test_cdata_string_plurals(self):
        self.maxDiff = None
        uploaded_openstring = OpenString("plurals_key", {1: "plural one", 5: "plural other"}, order=0)
        uploaded_openstring1 = OpenString("simple_string", "test string", order=1)
        uploaded_hash = uploaded_openstring.template_replacement
        uploaded_hash1 = uploaded_openstring1.template_replacement
        source= """
            <resources>
                <plurals name="plurals_key">
                    <item quantity="one"><![CDATA[plural one]]></item>
                    <item quantity="other"><![CDATA[plural other]]></item>
                </plurals>
                <string name="simple_string">test string</string>
            </resources>
        """
        cdata_source_python_template = f"""
            <resources>
                <plurals name="plurals_key">
                    {uploaded_hash}_cdata
                </plurals>
                <string name="simple_string">{uploaded_hash1}</string>
            </resources>
        """

        template, stringset = self.handler.parse(source)
         
        compiled = self.handler.compile(template, [uploaded_openstring,uploaded_openstring1])
        self.assertEqual(
            template,
            cdata_source_python_template,
        )
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, uploaded_openstring.__dict__)
        self.assertEqual(compiled, source)
        

    def test_cdata_string(self):
        self.maxDiff = None
        uploaded_openstring = OpenString("onshape_edu_plan", "<b>Onshape Education Plan</b>",\
                                          developer_comment="\nAdded by Transifex:CDATA", order=0)
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
    
    
    def test_create_string_raises_error(self):
        unescaped_string = "some ' string"
        self.assertRaises(
            ParseError,
            AndroidHandlerv3._check_unescaped_characters,
            unescaped_string,
        )
        unescaped_string = 'some " string'
        self.assertRaises(
            ParseError,
            AndroidHandlerv3._check_unescaped_characters,
            unescaped_string,
        )