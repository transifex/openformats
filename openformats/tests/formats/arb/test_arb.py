# -*- coding: utf-8 -*-

from os import path
import unittest

import six

from openformats.exceptions import ParseError
from openformats.formats.json import ArbHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (bytes_to_string,
                                             generate_random_string)


class ArbTestCase(CommonFormatTestMixin, unittest.TestCase):

    HANDLER_CLASS = ArbHandler
    TESTFILE_BASE = "openformats/tests/formats/arb/files"

    def setUp(self):
        super(ArbTestCase, self).setUp()
        filepath = path.join(self.TESTFILE_BASE, "1_en_exported.arb")
        with open(filepath, "r", encoding='utf-8') as myfile:
            self.data['1_en_exported'] = myfile.read()

        self.handler = ArbHandler()
        self.random_string = generate_random_string()
        self.random_openstring = OpenString("a", self.random_string, order=0)
        self.random_hash = self.random_openstring.template_replacement

    def test_simple(self):
        # Using old-timey string formatting because of conflicts with '{'
        template, stringset = self.handler.parse('{"a": "%s"}' %
                                                 self.random_string)
        self.assertEqual(template, '{"a": "%s"}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__,
                         self.random_openstring.__dict__)

        compiled = self.handler.compile(template, [self.random_openstring])
        self.assertEqual(compiled, '{"a": "%s"}' % self.random_string)

    def test_empty_string_ignored(self):
        _, stringset = self.handler.parse(
            '{"not_empty": "hello there", "empty": ""}'
        )
        self.assertEqual(len(stringset), 1)

    def test_empty_string_returned_in_compile(self):
        template, stringset = self.handler.parse('{"a": "%s", "b": ""}' %
                                                 self.random_string)
        compiled = self.handler.compile(template, [self.random_openstring])

        self.assertEqual(template, '{"a": "%s", "b": ""}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__,
                         self.random_openstring.__dict__)
        self.assertEqual(compiled, '{"a": "%s", "b": ""}' % self.random_string)

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en_exported"])

    def test_compile_skips_removed_strings_for_dicts(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)
        self.assertEqual(template, '{"a": "%s", "b": "%s"}' % (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)

        compiled = self.handler.compile(template, [openstring2], keep_sections=False)
        compiled = compiled.replace("{ ", "{").replace(" }", "}")  # fix spaces inside {}
        self.assertEqual(compiled, '{"b": "%s"}' % string2)

    def test_locale(self):
        source = '{"@@locale": "en_US", "a": "%s"}' % self.random_string
        template, stringset = self.handler.parse(source)
        self.assertEqual(template,
                         '{"@@locale": "en_US", "a": "%s"}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__,
                         self.random_openstring.__dict__)

        compiled = self.handler.compile(template, [self.random_openstring],
                                        language_info={"name": "French", "code": "fr"})
        self.assertEqual(compiled,
                         '{"@@locale": "fr", "a": "%s"}' % self.random_string)

    def test_whitespace_only_strings(self):
        self._test_parse_error('{"a": " ", "b": "   "}',
                               "No strings could be extracted")

    def test_remove_all_strings_removed_from_dict_but_non_strings_exist(self):
        random_string = self.random_string
        random_openstring = self.random_openstring
        random_hash = self.random_hash

        source = '{"a": "%s", "b": null}' % random_string

        template, stringset = self.handler.parse(source)
        self.assertEqual(template, '{"a": "%s", "b": null}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)

        compiled = self.handler.compile(template, [], keep_sections=False)
        self.assertEqual(compiled, '{ "b": null}')

    def test_skip_start_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring2 = OpenString('b', string2, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, _ = self.handler.parse(source)

        compiled = self.handler.compile(template, [openstring2], keep_sections=False)
        self.assertEqual(compiled, '{ "b": "%s"}' % string2)

    def test_skip_end_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString('a', string1, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, _ = self.handler.parse(source)

        compiled = self.handler.compile(template, [openstring1], keep_sections=False)
        self.assertEqual(compiled, '{"a": "%s"}' % string1)

    def test_skip_middle_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        string3 = generate_random_string()
        openstring1 = OpenString('a', string1, order=0)
        openstring3 = OpenString('c', string3, order=2)

        source = '{"a": "%s", "b": "%s", "c": "%s"}' % (string1, string2,
                                                        string3)
        template, _ = self.handler.parse(source)

        compiled = self.handler.compile(template, [openstring1, openstring3], keep_sections=False)
        self.assertEqual(compiled, '{"a": "%s", "c": "%s"}' % (string1,
                                                               string3))

    def test_invalid_json(self):
        try:
            self.handler.parse(u'jaosjf')
        except Exception as e:
            self.assertIn(six.text_type(e),
                          ("Expecting value: line 1 column 1 (char 0)",
                           "No JSON object could be decoded"))
        else:
            raise AssertionError("No parse error raised")

    def test_not_json_container(self):
        self._test_parse_error('"hello"',
                               'Was expecting whitespace or one of `[{` on line 1, found `"` instead')
        self._test_parse_error('3',
                               "Was expecting whitespace or one of `[{` on line 1, found `3` instead")
        self._test_parse_error('false',
                               "Was expecting whitespace or one of `[{` on line 1, found `f` instead")

    def test_skipping_stuff_within_strings(self):
        source = '{"a": "b,  ,c"}'
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

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
            self.assertEqual(ArbHandler.unescape(bytes_to_string(raw)),
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
            self.assertEqual(ArbHandler.escape(bytes_to_string(rich)),
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
            '    "k": "{cnt, plural,\\n zero {Empty} other {{count} files} \\n}"'  # noqa
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
        self.assertEqual(compiled, source)

    def test_non_supported_icu_argument(self):
        # Non-supported ICU arguments (everything other than `plural`)
        # should make a string be treated as non-pluralized

        string = '{"k": "{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }"}'  # noqa
        _, stringset = self.handler.parse(string)

        self.assertEqual(
            stringset[0].string,
            '{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }'  # noqa
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
            self.assertIn(msg_substr, six.text_type(e))
            error_raised = True
        self.assertTrue(error_raised)

    def _test_translations_equal(self, source, translations_by_rule):
        _, stringset = self.handler.parse(source)
        for rule_int in six.iterkeys(translations_by_rule):
            self.assertEqual(
                translations_by_rule[rule_int],
                stringset[0].string[rule_int]
            )
