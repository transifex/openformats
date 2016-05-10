# -*- coding: utf-8 -*-

import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import generate_random_string

from openformats.formats.json import JsonHandler


class JsonTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = JsonHandler
    TESTFILE_BASE = "openformats/tests/formats/beta_keyvaluejson/files"

    def setUp(self):
        super(JsonTestCase, self).setUp()

        self.handler = JsonHandler()
        self.random_string = generate_random_string()
        self.random_openstring = OpenString("a", self.random_string, order=0)
        self.random_hash = self.random_openstring.template_replacement

    def test_simple(self):
        # Using old-timey string formatting because of conflicts with '{'
        template, stringset = self.handler.parse('{"a": "%s"}' %
                                                 self.random_string)
        compiled = self.handler.compile(template, [self.random_openstring])

        self.assertEquals(template, '{"a": "%s"}' % self.random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__,
                          self.random_openstring.__dict__)
        self.assertEquals(compiled, '{"a": "%s"}' % self.random_string)

    def test_empty_string_ignored(self):
        template, stringset = self.handler.parse(
            '{"not_empty": "hello there", "empty": ""}'
        )
        self.assertEquals(len(stringset), 1)

        template, stringset = self.handler.parse(
            '{"not_empty": "hello there", "empty": [""]}'
        )
        self.assertEquals(len(stringset), 1)

    def test_root_object_is_list(self):
        source = '["%s"]' % self.random_string
        random_openstring = OpenString('..0..', self.random_string, order=0)
        random_hash = random_openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(template, '["%s"]' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_embedded_dicts(self):
        source = '{"a": {"b": "%s"}}' % self.random_string
        openstring = OpenString("a.b", self.random_string, order=0)
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEquals(template, '{"a": {"b": "%s"}}' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_embedded_lists(self):
        source = '{"a": ["%s"]}' % self.random_string
        openstring = OpenString("a..0..", self.random_string, order=0)
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEquals(template, '{"a": ["%s"]}' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_python_values_are_ignored(self):
        source = '[true, "%s", 5e12]' % self.random_string
        random_openstring = OpenString('..1..', self.random_string, order=0)
        random_hash = random_openstring.template_replacement
        template, stringset = self.handler.parse(source)
        self.assertEquals(template, '[true, "%s", 5e12]' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)

    def test_compile_skips_removed_strings_for_dicts(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(template, '{"a": "%s", "b": "%s"}' % (hash1, hash2))
        self.assertEquals(len(stringset), 2)
        self.assertEquals(stringset[0].__dict__, openstring1.__dict__)
        self.assertEquals(stringset[1].__dict__, openstring2.__dict__)
        self.assertEquals(compiled, '{"a": "%s"}' % string1)

    def test_compile_skips_removed_strings_for_lists(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)
        openstring2 = OpenString("..1..", string2, order=1)
        hash1 = openstring1.template_replacement
        hash2 = openstring2.template_replacement

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(template, '["%s", "%s"]' % (hash1, hash2))
        self.assertEquals(len(stringset), 2)
        self.assertEquals(stringset[0].__dict__, openstring1.__dict__)
        self.assertEquals(stringset[1].__dict__, openstring2.__dict__)
        self.assertEquals(compiled, '["%s"]' % string1)

    def test_compile_skips_removed_nested_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)
        openstring2 = OpenString("..1...a", string2, order=1)
        hash1 = openstring1.template_replacement
        hash2 = openstring2.template_replacement

        source = '["%s", {"a": "%s"}]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(template, '["%s", {"a": "%s"}]' % (hash1, hash2))
        self.assertEquals(len(stringset), 2)
        self.assertEquals(stringset[0].__dict__, openstring1.__dict__)
        self.assertEquals(stringset[1].__dict__, openstring2.__dict__)
        self.assertEquals(compiled, '["%s"]' % string1)

    def test_compile_skips_removed_nested_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b..0..", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = '{"a": "%s", "b": ["%s"]}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(template,
                          '{"a": "%s", "b": ["%s"]}' % (hash1, hash2))
        self.assertEquals(len(stringset), 2)
        self.assertEquals(stringset[0].__dict__, openstring1.__dict__)
        self.assertEquals(stringset[1].__dict__, openstring2.__dict__)
        self.assertEquals(compiled, '{"a": "%s"}' % string1)

    def test_remove_all_strings_removed_from_list_but_non_strings_exist(self):
        random_string = self.random_string
        random_openstring = OpenString('a..1..', random_string, order=0)
        random_hash = random_openstring.template_replacement

        source = '{"a": [null, "%s"]}' % random_string

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])

        self.assertEquals(template, '{"a": [null, "%s"]}' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, '{"a": [null]}')

    def test_remove_all_strings_removed_from_dict_but_non_strings_exist(self):
        random_string = self.random_string
        random_openstring = self.random_openstring
        random_hash = self.random_hash

        source = '{"a": "%s", "b": null}' % random_string

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])

        self.assertEquals(template, '{"a": "%s", "b": null}' % random_hash)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, '{ "b": null}')

    def test_skip_start_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring2 = OpenString('b', string2, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring2])

        self.assertEquals(compiled, '{ "b": "%s"}' % string2)

    def test_skip_end_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString('a', string1, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(compiled, '{"a": "%s"}' % string1)

    def test_skip_middle_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        string3 = generate_random_string()
        openstring1 = OpenString('a', string1, order=0)
        openstring3 = OpenString('c', string3, order=2)

        source = '{"a": "%s", "b": "%s", "c": "%s"}' % (string1, string2,
                                                        string3)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1, openstring3])

        self.assertEquals(compiled, '{"a": "%s", "c": "%s"}' % (string1,
                                                                string3))

    def test_skip_start_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring2 = OpenString('..1..', string2, order=1)

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring2])

        self.assertEquals(compiled, '[ "%s"]' % string2)

    def test_skip_end_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString('..0..', string1, order=0)

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEquals(compiled, '["%s"]' % string1)

    def test_skip_middle_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        string3 = generate_random_string()
        openstring1 = OpenString('..0..', string1, order=0)
        openstring3 = OpenString('..2..', string3, order=2)

        source = '["%s", "%s", "%s"]' % (string1, string2, string3)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1, openstring3])

        self.assertEquals(compiled, '["%s", "%s"]' % (string1, string3))

    def test_invalid_json(self):
        self._test_parse_error('jaosjf', "No JSON object could be decoded")

    def test_invalid_json_type(self):
        template, stringset = self.handler.parse('[false]')
        self.assertEqual(stringset, [])
        self.assertEqual(template, '[false]')

        template, stringset = self.handler.parse('{"false": false}')
        self.assertEqual(stringset, [])
        self.assertEqual(template, '{"false": false}')

    def test_not_json_container(self):
        self._test_parse_error('"hello"',
                               'Was expecting whitespace or one of `{[` on '
                               'line 1, found `"` instead')
        self._test_parse_error('3',
                               "Was expecting whitespace or one of `{[` on "
                               "line 1, found `3` instead")
        self._test_parse_error('false',
                               "Was expecting whitespace or one of `{[` on "
                               "line 1, found `f` instead")

    def test_skipping_stuff_within_strings(self):
        source = '{"a": "b,  ,c"}'
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEquals(compiled, source)

    def test_duplicate_keys(self):
        self._test_parse_error('{"a": "hello", "a": "world"}',
                               "Duplicate string key ('a') in line 1")

    def test_display_json_errors(self):
        self._test_parse_error('["]',
                               "Unterminated string starting at: line 1 "
                               "column 2 (char 1)")

    def test_escape_json(self):
        self.assertEqual(
            self.handler.escape("a \\ string. with \"quotes\""),
            "a \\\\ string. with \\\"quotes\\\""
        )

        self.assertEqual(
            self.handler.escape(u'καλημέρα \\'), u'καλημέρα \\\\'
        )

    def test_unescape_json(self):
        self.assertEqual(
            self.handler.unescape("a \\\\ string. with \\\"quotes\\\""),
            "a \\ string. with \"quotes\""
        )

        self.assertEqual(
            self.handler.unescape(u'καλημέρα \\\\'),
            u'καλημέρα \\'
        )
