# -*- coding: utf-8 -*-

import unittest

from openformats.formats.json import JsonHandler

from openformats.exceptions import ParseError
from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (generate_random_string,
                                             bytes_to_string)


class JsonTestCase(CommonFormatTestMixin, unittest.TestCase):

    HANDLER_CLASS = JsonHandler
    TESTFILE_BASE = "openformats/tests/formats/keyvaluejson/files"

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

    def test_unescape(self):
        cases = (
            # simple => simple
            ([u's', u'i', u'm', u'p', u'l', u'e'],
             [u's', u'i', u'm', u'p', u'l', u'e']),
            # hεllo => hεllo
            ([u'h', u'ε', u'l', u'l', u'o'],
             [u'h', u'ε', u'l', u'l', u'o']),
            # h\u03b5llo => hεllo
            ([u'h', u'\\', u'u', u'0', u'3', u'b', u'5', u'l', u'l', u'o'],
             [u'h', u'ε', u'l', u'l', u'o']),
            # a\"b => a"b
            ([u'a', u'\\', u'"', u'b'], [u'a', u'"', u'b']),
            # a\/b => a/b
            ([u'a', u'\\', u'/', u'b'], [u'a', u'/', u'b']),
            # a\/b => a?b, ? = BACKSPACE
            ([u'a', u'\\', u'b', u'b'], [u'a', u'\b', u'b']),
            # a\fb => a?b, ? = FORMFEED
            ([u'a', u'\\', u'f', u'b'], [u'a', u'\f', u'b']),
            # a\nb => a?b, ? = NEWLINE
            ([u'a', u'\\', u'n', u'b'], [u'a', u'\n', u'b']),
            # a\rb => a?b, ? = CARRIAGE_RETURN
            ([u'a', u'\\', u'r', u'b'], [u'a', u'\r', u'b']),
            # a\tb => a?b, ? = TAB
            ([u'a', u'\\', u't', u'b'], [u'a', u'\t', u'b']),
        )
        for raw, rich in cases:
            self.assertEquals(JsonHandler.unescape(bytes_to_string(raw)),
                              bytes_to_string(rich))

    def test_escape(self):
        cases = (
            # simple => simple
            ([u's', u'i', u'm', u'p', u'l', u'e'],
             [u's', u'i', u'm', u'p', u'l', u'e']),
            # hεllo => hεllo
            ([u'h', u'ε', u'l', u'l', u'o'],
             [u'h', u'ε', u'l', u'l', u'o']),
            # h\u03b5llo => h\\u03b5llo
            ([u'h', u'\\', u'u', u'0', u'3', u'b', u'5', u'l', u'l', u'o'],
             [u'h', u'\\', u'\\', u'u', u'0', u'3', u'b', u'5', u'l', u'l',
              u'o']),
            # a"b =>a\"b
            ([u'a', u'"', u'b'], [u'a', u'\\', u'"', u'b']),
            # a/b =>a/b
            ([u'a', u'/', u'b'], [u'a', u'/', u'b']),
            # a?b =>a\/b, ? = BACKSPACE
            ([u'a', u'\b', u'b'], [u'a', u'\\', u'b', u'b']),
            # a?b =>a\fb, ? = FORMFEED
            ([u'a', u'\f', u'b'], [u'a', u'\\', u'f', u'b']),
            # a?b =>a\nb, ? = NEWLINE
            ([u'a', u'\n', u'b'], [u'a', u'\\', u'n', u'b']),
            # a?b =>a\rb, ? = CARRIAGE_RETURN
            ([u'a', u'\r', u'b'], [u'a', u'\\', u'r', u'b']),
            # a?b => a\tb, ? = TAB
            ([u'a', u'\t', u'b'], [u'a', u'\\', u't', u'b']),
        )
        for rich, raw in cases:
            self.assertEquals(JsonHandler.escape(bytes_to_string(rich)),
                              bytes_to_string(raw))

    # PLURALS

    def test_invalid_plural_format(self):
        # Test various cases of messed-up braces
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have file_count} file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file. other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file}. other {You have file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )

    def test_invalid_plural_rules(self):
        # Only the following strings are allowed as plural rules:
        #   zero, one, few, many, other
        # Anything else, including their TX int equivalents are invalid.
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, 1 {file} 5 {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "1, 5" in pluralized entry with key: total_files'  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, once {file} mother {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "once, mother" in pluralized entry with key: total_files'  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, =3 {file} other {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "=3" in pluralized entry with key: total_files'  # noqa
        )

    def test_irrelevant_whitespace_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        expected_translations = {0: 'Empty', 5: '{count} files'}

        self._test_translations_equal(
            '{'
            '    "k": "{ cnt, plural, zero {Empty} other {{count} files} }"'
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": "{cnt,plural,zero{Empty}other{{count} files} }"'
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{ "k": "{    cnt,  plural,     zero  {Empty} other   {{count} files} }   "     }',  # noqa
            expected_translations
        )
        self._test_translations_equal(
            '     {'
            '    "k": "{cnt,plural,zero{Empty}other{{count} files} }"'
            '}  ',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": "  {cnt, plural, zero {Empty} other {{count} files} }"'
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": "{cnt , plural , zero {Empty} other {{count} files} }"'
            '}',
            expected_translations
        )

        # Escaped new lines should be allowed
        self._test_translations_equal(
            '{'
            '    "k": "{cnt, plural,\\n zero {Empty} other {{count} files} \\n}"'  #noqa
            '}',
            expected_translations
        )

        # Rendering a template with escaped new lines should work. However,
        # these characters cannot be inside the pluralized string, because the
        # template would be very hard to create in that case (e.g. not allowed
        # in: 'zero {Empty} \n other {{count} files}'
        source = '{"a": "{cnt, plural,\\n one {0} other {{count} files} \\n}"}'
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEquals(compiled, source)

    def test_non_supported_icu_argument(self):
        # Non-supported ICU arguments (everything other than `plural`)
        # should make a string be treated as non-pluralized

        string = '{"k": "{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }"}'  # noqa
        _, stringset = self.handler.parse(string)

        self.assertEqual(
            stringset[0].string,
            '{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }'
        )

    def test_nesting_with_plurals(self):
        expected_translations = {0: 'Empty', 5: '{count} files'}

        self._test_translations_equal(
            '{ "k": { "a": "{ cnt, plural, zero {Empty} other {{count} files} }", "b": "c" } }',  # noqa
            expected_translations
        )

    def test_whitespace_in_translations_not_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty} other {{count} files} }"}',
            {0: ' Empty', 5: '{count} files'}
        )
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty  } other {{count} files } }"}',
            {0: ' Empty  ', 5: '{count} files '}
        )

    def _test_parse_error_message(self, source, msg_substr):
        error_raised = False
        try:
            self.handler.parse(source)
        except ParseError as e:
            self.assertIn(
                msg_substr,
                e.message
            )
            error_raised = True
        self.assertTrue(error_raised)

    def _test_translations_equal(self, source, translations_by_rule):
        template, stringset = self.handler.parse(source)
        for rule_int in translations_by_rule.keys():
            self.assertEqual(
                translations_by_rule[rule_int],
                stringset[0].string[rule_int]
            )
