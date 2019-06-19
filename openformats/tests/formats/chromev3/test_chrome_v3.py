from __future__ import unicode_literals

import json
import unittest

from openformats.exceptions import ParseError
from openformats.formats.json import ChromeI18nHandlerV3
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import generate_random_string


class ChromeI18nV3TestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = ChromeI18nHandlerV3
    TESTFILE_BASE = "openformats/tests/formats/chromev3/files"

    def setUp(self):
        super(ChromeI18nV3TestCase, self).setUp()
        self.random_string = generate_random_string()
        self.random_openstring = OpenString('a', self.random_string, order=0,
                                            developer_comment='')

    def test_simple(self):
        source_template = '{"a": {"message": "%s"}}'
        source = source_template % self.random_string
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [self.random_openstring])

        self.assertEqual(
            template,
            source_template % self.random_openstring.template_replacement
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__,
                         self.random_openstring.__dict__)
        self.assertEqual(compiled, source)
        # Check developer comment is empty
        self.assertEqual(stringset[0].developer_comment, '')

    def test_invalid_json(self):
        with self.assertRaises(ParseError):
            self.handler.parse('{')
        with self.assertRaises(ParseError):
            self.handler.parse('3')
        self._test_parse_error('[]', u"Source file must be a JSON object")

    def test_double_key(self):
        self._test_parse_error('{"a": 1, "a": 2}',
                               u"Key 'a' appears multiple times (line 1)")

    def test_pluralized_string(self):
        source_template = '{"a": {"message": "{cnt, plural, %s}"}}'
        source = source_template % "one {horse} other {horses}"
        openstring = OpenString('a', {1: "horse", 5: "horses"},
                                pluralized=True, order=0, developer_comment='')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template,
                         source_template % openstring.template_replacement)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)
        # Check developer comment is empty
        self.assertEqual(stringset[0].developer_comment, '')

    def test_remove_strings(self):
        """ Start with a source file with 3 strings and test the parsing
            process as always. Then compile it 3 times. Each time, as the
            stringset use 2 of the 3 original strings. Make sure the compiled
            file is a valid JSON string and that it only includes the strings
            that were in the stringset.
        """

        source_template = ('{"a": {"message": "%s"}, "b": {"message": "%s"},'
                           ' "c": {"message": "%s"}}')
        source = source_template % ("aaa", "bbb", "ccc")
        openstring_a = OpenString('a', "aaa", order=0, developer_comment='')
        openstring_b = OpenString('b', "bbb", order=1, developer_comment='')
        openstring_c = OpenString('c', "ccc", order=2, developer_comment='')
        template, stringset = self.handler.parse(source)

        self.assertEqual(template,
                         source_template % (openstring_a.template_replacement,
                                            openstring_b.template_replacement,
                                            openstring_c.template_replacement))
        self.assertEqual(len(stringset), 3)
        self.assertEqual([string.__dict__ for string in stringset],
                         [openstring_a.__dict__,
                          openstring_b.__dict__,
                          openstring_c.__dict__])

        # We will compare the dict versions of the strings because the way the
        # compiler leaves over some whitespaces when removing sections makes
        # the serialized versions a bit unpredictable

        # Remove first string
        compiled = self.handler.compile(template, [openstring_b, openstring_c])
        self.assertEqual(json.loads(compiled),
                         {'b': {'message': "bbb"}, 'c': {'message': "ccc"}})

        # Remove second string
        compiled = self.handler.compile(template, [openstring_a, openstring_c])
        self.assertEqual(json.loads(compiled),
                         {'a': {'message': "aaa"}, 'c': {'message': "ccc"}})

        # Remove third string
        compiled = self.handler.compile(template, [openstring_a, openstring_b])
        self.assertEqual(json.loads(compiled),
                         {'a': {'message': "aaa"}, 'b': {'message': "bbb"}})
