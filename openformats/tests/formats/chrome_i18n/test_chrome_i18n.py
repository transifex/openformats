# -*- coding: utf-8 -*-

import unittest
import json

from openformats.formats.json import ChromeI18nHandler

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import generate_random_string
from openformats.exceptions import ParseError


class ChromeI18nTestCase(CommonFormatTestMixin, unittest.TestCase):

    HANDLER_CLASS = ChromeI18nHandler
    TESTFILE_BASE = "openformats/tests/formats/chrome_i18n/files"

    def setUp(self):
        super(ChromeI18nTestCase, self).setUp()

        self.handler = ChromeI18nHandler()
        self.random_string = generate_random_string()
        self.random_openstring = OpenString("a.message", "%s" %
                                            self.random_string, order=0)
        self.random_hash = self.random_openstring.template_replacement

    def test_simple(self):
        source = '{"a":{"message": "%s"}}' % self.random_string
        template, stringset = self.handler.parse('{"a":{"message": "%s"}}' %
                                                 self.random_string)
        compiled = self.handler.compile(template, [self.random_openstring])
        self.assertEquals(
            template, '{"a":{"message": "%s"}}' % self.random_hash
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__,
                          self.random_openstring.__dict__)
        self.assertEquals(
            compiled, '{"a":{"message": "%s"}}' % self.random_string
        )
        # Check developer comment is empty
        self.assertEquals(stringset[0].developer_comment, "")
        # Check the JSON dict lives in memory and contains the whole source
        self.assertEquals(json.loads(source), self.handler.json_dict)

    def test_with_description(self):
        source = '{"a":{"message":"%s","description":"desc"}}'
        template, stringset = self.handler.parse(source % self.random_string)

        self.assertEquals(len(stringset), 1)
        self.assertEquals(template, source % self.random_hash)
        # Check that description has been assigned to the correct field
        self.assertEquals(stringset[0].developer_comment, "desc")

    def test_with_template(self):
        source = '{"a":{"message":"%s","description":"desc","garbage":"text"}}'
        template, stringset = self.handler.parse(source % self.random_string)

        self.assertEquals(len(stringset), 1)
        self.assertEquals(template, source % self.random_hash)
        compiled = self.handler.compile(template, [self.random_openstring])
        # Check that additional keys/values are part of the template
        self.assertEquals(compiled, source % self.random_string)

    def test_no_message_or_description(self):
        source = '{"a":{"random-key":"random-value","garbage":"text"}}'
        template, stringset = self.handler.parse(source)

        self.assertEquals(len(stringset), 0)
        self.assertEquals(template, source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, source)

    def test_unicode_source_and_description(self):
        self.random_string = u'τεστ'
        self.random_openstring = OpenString("a.message", "%s" %
                                            self.random_string, order=0)
        self.random_hash = self.random_openstring.template_replacement

        source = u'{"a":{"message":"%s","description":"τεστ","τεστ":"τεστ"}}'
        template, stringset = self.handler.parse(source % self.random_string)

        self.assertEquals(len(stringset), 1)
        self.assertEquals(template, source % self.random_hash)
        compiled = self.handler.compile(template, [self.random_openstring])
        self.assertEquals(compiled, source % self.random_string)

    def test_with_integers_as_values(self):
        source = '{"a":{"message":"%s","description":1234, "123":"123"}}'
        template, stringset = self.handler.parse(source % self.random_string)

        self.assertEquals(len(stringset), 1)
        self.assertEquals(template, source % self.random_hash)
        self.assertEquals(stringset[0].developer_comment, 1234)

    def test_invalid_json(self):
        source = '{"a":{123:"%s"}}'
        with self.assertRaises(ParseError):
            template, stringset = self.handler.parse(
                source % self.random_string
            )

    def test_with_extra_characters_as_value(self):
        source = '{"a":{"message":"%s", "@@@@description":"desc"}}'
        template, stringset = self.handler.parse(source % self.random_string)

        self.assertEquals(len(stringset), 1)
        self.assertEquals(template, source % self.random_hash)
        self.assertEquals(stringset[0].developer_comment, "")
