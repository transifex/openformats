import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string, strip_leading_spaces
)

from openformats.formats.android import AndroidHandler


class AndroidTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidHandler
    TESTFILE_BASE = "openformats/tests/formats/beta_android/files"

    def setUp(self):
        super(AndroidTestCase, self).setUp()
        self.handler = AndroidHandler()

    def test_string(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        random_openstring = OpenString(random_key,
                                       random_string, order=0)
        random_hash = random_openstring.template_replacement

        source_python_template = u'''
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        '''
        source = source_python_template.format(key=random_key,
                                               string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            source_python_template.format(key=random_key, string=random_hash)
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_string_array(self):
        random_name = generate_random_string()
        random_key = '{}[0]'.format(random_name)
        random_string = generate_random_string()
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement
        source_python_template = strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item>{string}</item>
                </string-array>
            </resources>
        ''')
        source = source_python_template.format(key=random_name,
                                               string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            source_python_template.format(key=random_name, string=random_hash)
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__,
                          random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_plurals(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        random_openstring = OpenString(random_key,
                                       {1: random_singular, 5: random_plural},
                                       order=0)
        random_hash = random_openstring.template_replacement

        source = strip_leading_spaces(u"""
            <resources>
                <plurals name="{key}">
                    <item quantity="one">{singular}</item>
                    <item quantity="other">{plural}</item>
                </plurals>
            </resources>
        """.format(key=random_key, singular=random_singular,
                   plural=random_plural))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            strip_leading_spaces(u'''
                <resources>
                    <plurals name="{key}">
                        {hash_}
                    </plurals>
                </resources>
            '''.format(key=random_key, hash_=random_hash))
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)
