# -*- coding: utf-8 -*-

import unittest
import six

from openformats.formats.json import StructuredJsonHandler

from openformats.exceptions import ParseError
from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (generate_random_string,
                                             bytes_to_string)


class StructuredJsonTestCase(CommonFormatTestMixin, unittest.TestCase):

    HANDLER_CLASS = StructuredJsonHandler
    TESTFILE_BASE = "openformats/tests/formats/structuredkeyvaluejson/files"

    def setUp(self):
        super(StructuredJsonTestCase, self).setUp()

        self.handler = StructuredJsonHandler()
        self.random_string = generate_random_string()
        self.pluralized_string = "{ item_count, plural, one {You have {file_count} file.} other {You have {file_count} files.} }" # noqa

        self.random_openstring = OpenString("a",
                                            self.random_string, order=0)
        self.random_hash = self.random_openstring.template_replacement

    def test_simple(self):
        template, stringset = self.handler.parse('{"a": {"string":"%s"}}' %
                                                 self.random_string)
        compiled = self.handler.compile(template, [self.random_openstring])
        self.assertEqual(template,
                         '{"a": {"string":"%s"}}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__,
                         self.random_openstring.__dict__)
        self.assertEqual(compiled,
                         '{"a": {"string":"%s"}}' % self.random_string)
    
    def test_dots_in_key(self):
        first_level_key = "a.b"
        source = '{"%s": {"c": {"string": "%s"}}}' % (first_level_key, self.random_string)
        openstring = OpenString(
            "{}.c".format(self.handler._escape_key(first_level_key)), 
            self.random_string, order=0
        )
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template,
                         '{"a.b": {"c": {"string": "%s"}}}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_escaped_character_in_key(self):
        first_level_key = "a\/b"
        source = '{"%s": {"c": {"string": "%s"}}}' % (first_level_key, self.random_string)
        openstring = OpenString(
            "{}.c".format(self.handler._escape_key(first_level_key)), 
            self.random_string, order=0
        )
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template,
                         '{"a\/b": {"c": {"string": "%s"}}}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_embedded_dicts(self):
        source = '{"a": {"b": {"string": "%s"}}}' % self.random_string
        openstring = OpenString("a.b", self.random_string, order=0)
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template,
                         '{"a": {"b": {"string": "%s"}}}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_compile_ignores_removed_strings_for_dicts(self):
        # The original JsonHandler, when compiling back from a template,
        # removes any strings that are not passed as an argument in the
        # compile() function. StructuredJsonHandler on the other hand, simply
        # ignores those key-values and leave them as is in the template. This
        # test ensures that this is the case.
        # For more information, see _copy_until_and_remove_section() in both
        # handlers.
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = ('{"a": {"string":"%s"}, "b": {"string":"%s"}}' %
                  (string1, string2))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring1])

        self.assertEqual(template,
                         '{"a": {"string":"%s"}, "b": {"string":"%s"}}' %
                         (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)
        self.assertEqual(
            compiled,
            '{"a": {"string":"%s"}, "b": {"string":"%s"}}' % (string1, hash2)
        )

    def test_invalid_json(self):
        with self.assertRaises(ParseError) as context:
            self.handler.parse(u'invalid_json')

        self.assertIn(six.text_type(context.exception),
                      ("Expecting value: line 1 column 1 (char 0)",
                       "No JSON object could be decoded"))

    def test_invalid_json_type(self):
        template, stringset = self.handler.parse('[false]')
        self.assertEqual(stringset, [])
        self.assertEqual(template, '[false]')

        template, stringset = self.handler.parse('{"false": false}')
        self.assertEqual(stringset, [])
        self.assertEqual(template, '{"false": false}')

    def test_not_json_container(self):
        self._test_parse_error('"hello"',
                               'Was expecting whitespace or one of `[{` on '
                               'line 1, found `"` instead')
        self._test_parse_error('3',
                               "Was expecting whitespace or one of `[{` on "
                               "line 1, found `3` instead")
        self._test_parse_error('false',
                               "Was expecting whitespace or one of `[{` on "
                               "line 1, found `f` instead")

    def test_skipping_stuff_within_strings(self):
        source = '{"a": {"string":"b,  ,c"}}'
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_duplicate_keys(self):
        self._test_parse_error('{"a": {"string": "hello"}, "a": {"string": "hello"}}', # noqa
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
            self.assertEqual(StructuredJsonHandler.unescape(
                bytes_to_string(raw)), bytes_to_string(rich)
            )

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
            self.assertEqual(StructuredJsonHandler.escape(
                bytes_to_string(rich)), bytes_to_string(raw)
            )

    # PLURALS

    def test_invalid_plural_format(self):
        # Test various cases of messed-up braces
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, one {You have {file_count file.} other {You have {file_count} files.} }" }}',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, one {You have file_count} file.} other {You have {file_count} files.} }" }}',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, one {You have {file_count} file. other {You have {file_count} files.} }" }}',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, one {You have {file_count} file}. other {You have file_count} files.} }" }}',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )

    def test_invalid_plural_rules(self):
        # Only the following strings are allowed as plural rules:
        #   zero, one, few, many, other
        # Anything else, including their TX int equivalents are invalid.
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, 1 {file} 5 {{file_count} files} }" }}',  # noqa
            'Invalid plural rule(s): "1, 5" in pluralized entry with key: total_files'  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, once {file} mother {{file_count} files} }" }}',  # noqa
            'Invalid plural rule(s): "once, mother" in pluralized entry with key: total_files'  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": {"string": "{ item_count, plural, =3 {file} other {{file_count} files} }" }}',  # noqa
            'Invalid plural rule(s): "=3" in pluralized entry with key: total_files'  # noqa
        )

    def test_irrelevant_whitespace_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        expected_translations = {0: 'Empty', 5: '{count} files'}

        self._test_translations_equal(
            '{'
            '    "k": {"string": "{ cnt, plural, zero {Empty} other {{count} files} }"}' # noqa
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": {"string": "{cnt,plural,zero{Empty}other{{count} files} }"}' # noqa
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{ "k": {"string": "{    cnt,  plural,     zero  {Empty} other   {{count} files} }   "     }}',  # noqa
            expected_translations
        )
        self._test_translations_equal(
            '     {'
            '    "k": {"string": "{cnt,plural,zero{Empty}other{{count} files} }"}' # noqa
            '}  ',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": {"string": "  {cnt, plural, zero {Empty} other {{count} files} }"}' # noqa
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": {"string": "{cnt , plural , zero {Empty} other {{count} files} }"}' # noqa
            '}',
            expected_translations
        )

        # Escaped new lines should be allowed
        self._test_translations_equal(
            '{'
            '    "k": {"string": "{cnt, plural,\\n zero {Empty} other {{count} files} \\n}"}'  # noqa
            '}',
            expected_translations
        )

        # Rendering a template with escaped new lines should work. However,
        # these characters cannot be inside the pluralized string, because the
        # template would be very hard to create in that case (e.g. not allowed
        # in: 'zero {Empty} \n other {{count} files}'
        source = '{"a": {"string": "{cnt, plural,\\n one {0} other {{count} files} \\n}"}}' # noqa
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_non_supported_icu_argument(self):
        # Non-supported ICU arguments (everything other than `plural`)
        # should make a string be treated as non-pluralized

        string = '{"k": {"string" :"{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }"}}'  # noqa
        _, stringset = self.handler.parse(string)

        self.assertEqual(
            stringset[0].string,
            '{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }' # noqa
        )

    def test_nesting_with_plurals(self):
        expected_translations = {0: 'Empty', 5: '{count} files'}

        self._test_translations_equal(
            '{ "k": { "a": {"string" :"{ cnt, plural, zero {Empty} other {{count} files} }", "b": "c" } }}',  # noqa
            expected_translations
        )

    def test_whitespace_in_translations_not_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        self._test_translations_equal(
            '{"k": {"string": "{ cnt, plural, zero { Empty} other {{count} files} }"}}', # noqa
            {0: ' Empty', 5: '{count} files'}
        )
        self._test_translations_equal(
            '{"k": {"string": "{ cnt, plural, zero { Empty  } other {{count} files } }"}}', # noqa
            {0: ' Empty  ', 5: '{count} files '}
        )

    def test_openstring_structure(self):
        _, stringset = self.handler.parse(
            '{"a": {"string":"%s", "developer_comment": "developer_comment",'
            '"character_limit": 150, "context": "context"}}'
            % self.random_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].string, self.random_string)
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].character_limit, 150)
        self.assertEqual(stringset[0].context, "context")

    def test_openstring_structure_with_nested_format(self):
        _, stringset = self.handler.parse(
            '{"a": {"level": {"string":"%s", "developer_comment": "developer_comment",' # noqa
            '"character_limit": 150, "context": "context"}}}'
            % self.random_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].string, self.random_string)
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].character_limit, 150)
        self.assertEqual(stringset[0].context, "context")

    def test_openstring_structure_with_default_values(self):
        _, stringset = self.handler.parse(
            '{"a": {"string":"%s"}}' % self.random_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].string, self.random_string)
        self.assertEqual(stringset[0].developer_comment, "")
        self.assertEqual(stringset[0].character_limit, None)
        self.assertEqual(stringset[0].context, "")

    def test_pluralized_openstring_structure(self):
        _, stringset = self.handler.parse(
            '{"a": {"string":"%s", "developer_comment": "developer_comment",'
            '"character_limit": 150, "context": "context"}}'
            % self.pluralized_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].character_limit, 150)
        self.assertEqual(stringset[0].context, "context")

    def test_pluralized_openstring_structure_with_nested_format(self):
        _, stringset = self.handler.parse(
            '{"a": {"level": {"string":"%s", "developer_comment": "developer_comment",' # noqa
            '"character_limit": 150, "context": "context"}}}'
            % self.pluralized_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].developer_comment, "developer_comment")
        self.assertEqual(stringset[0].character_limit, 150)
        self.assertEqual(stringset[0].context, "context")

    def test_pluralized_openstring_structure_with_default_values(self):
        _, stringset = self.handler.parse(
            '{"a": {"string":"%s"}}' % self.pluralized_string
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].developer_comment, "")
        self.assertEqual(stringset[0].character_limit, None)
        self.assertEqual(stringset[0].context, "")

    def _test_parse_error_message(self, source, msg_substr):
        error_raised = False
        try:
            self.handler.parse(source)
        except ParseError as e:
            self.assertIn(msg_substr, six.text_type(e))
            error_raised = True
        self.assertTrue(error_raised)

    def _test_translations_equal(self, source, translations_by_rule):
        template, stringset = self.handler.parse(source)
        for rule_int in six.iterkeys(translations_by_rule):
            self.assertEqual(
                translations_by_rule[rule_int],
                stringset[0].string[rule_int]
            )

    def test_list_in_children_left_untouched(self):
        source = '{"a": {"string":"%s", "developer_comment": "developer_comment",' \
                 '"character_limit": 150, "context": "context"}, "b": [1, "a", "b"]}' % self.pluralized_string

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_compile_when_root_is_list(self):
        source = '[{"a": {"string":"%s", "developer_comment": "developer_comment",' \
                 '"character_limit": 150, "context": "context"}, "b": [1, "a", "b"]}]' % self.pluralized_string

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_template_with_existing_values(self):
        source = """
        {
            "a": {
                "character_limit":150, 
                "string":"%s",
                "developer_comment": "i am a developer",
                "context": "contexttt"
            }
        }
        """ % self.random_string

        expected_compilation = """
        {
            "a": {
                "character_limit":49, 
                "string":"%s",
                "developer_comment": "comment_changed",
                "context": "context_changed"
            }
        }
        """ % self.random_string

        template, stringset = self.handler.parse(source)

        with_updated_char_limit = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].strings,
                context="context_changed",
                developer_comment="comment_changed",
                character_limit=49,
            )
        ]

        compiled = self.handler.compile(template, with_updated_char_limit)
        self.assertEqual(compiled, expected_compilation)

    def test_template_with_values_defined_after_template(self):
        source = """
        {
            "a": {
                "string": "%s"
            }
        }
        """ % self.random_string

        expected_compilation = """
        {
            "a": {
                "string": "%s",
                "context": "the_context",
                "character_limit": 49,
                "developer_comment": "the_comment"
            }
        }
        """ % self.random_string
        template, stringset = self.handler.parse(source)

        updated_strings = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].strings,
                context="the_context",
                developer_comment="the_comment",
                character_limit=49,
            )
        ]

        compiled = self.handler.compile(template, updated_strings)
        self.assertEqual(compiled, expected_compilation)

    def test_template_with_values_removed_after_template(self):
        source = """
        {
            "a": {
                "string":"%s",
                "developer_comment":"i am a developer",
                "character_limit":150,
                "context":"contexttt"
            }
        }
        """ % self.random_string

        expected_compilation = """
        {
            "a": {
                "string":"%s",
                "developer_comment":"",
                "character_limit":null,
                "context":""
            }
        }
        """ % self.random_string
        template, stringset = self.handler.parse(source)

        updated_strings = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].strings,
                context='',
                developer_comment='',
                character_limit=None,
            )
        ]

        compiled = self.handler.compile(template, updated_strings)
        self.assertEqual(compiled, expected_compilation)

    def test_template_separators(self):
        source = '{"a": {\n    "string": "%s"}}' % self.random_string
        expected_compilation = '{"a": {\n    "string": "%s",\n    "character_limit": 153}}' % self.random_string
        template, stringset = self.handler.parse(source)

        with_updated_char_limit = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].strings,
                context=stringset[0].context,
                developer_comment=stringset[0].developer_comment,
                character_limit=153,
            )
        ]

        compiled = self.handler.compile(template, with_updated_char_limit)
        self.assertEqual(compiled, expected_compilation)

    def test_unicode(self):
        source = u"""
        {
            "a": {
                "string": "%s",
                "something_else": "\xa0"
            }
        }
        """ % self.random_string

        expected_compilation = u"""
        {
            "a": {
                "string": "\xa0",
                "something_else": "\xa0"
            }
        }
        """
        template, stringset = self.handler.parse(source)

        with_updated_char_limit = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=u"\xa0",
                context=stringset[0].context,
                developer_comment=stringset[0].developer_comment,
                character_limit=stringset[0].character_limit,
            )
        ]

        compiled = self.handler.compile(template, with_updated_char_limit)
        self.assertEqual(compiled, expected_compilation)

    def test_unescaped(self):
        source = u"""
        {
            "a": {
                "string": "testtest",
                "context": "context",
                "developer_comment": "comments"
            },
            "b": {
                "string": "testtest2"
            }
        }
        """

        expected_compilation = u"""
        {
            "a": {
                "string": "testtest",
                "context": "other \\" context",
                "developer_comment": "other \\" comment"
            },
            "b": {
                "string": "testtest2",
                "context": "other \\" context",
                "developer_comment": "other \\" comment"
            }
        }
        """
        template, stringset = self.handler.parse(source)

        unescaped = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context=u'other " context',
                developer_comment=u'other " comment',
                character_limit=stringset[0].character_limit,
            ),
            OpenString(
                key=stringset[1].key,
                string_or_strings=stringset[1].string,
                context=u'other " context',
                developer_comment=u'other " comment',
                character_limit=stringset[1].character_limit,
            )
        ]

        compiled = self.handler.compile(template, unescaped)
        self.maxDiff = None
        self.assertEqual(compiled, expected_compilation)

    def test_empty_string(self):
        source = u"""
        {
            "a": {
                "string": ""
            },
            "b": {
                "string": "x0x0",
                "character_limit": 35
            }
        }
        """

        expected_compilation = u"""
        {
            "a": {
                "string": ""
            },
            "b": {
                "string": "x0x0",
                "character_limit": 35
            }
        }
        """
        template, stringset = self.handler.parse(source)

        expected = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context=stringset[0].context,
                developer_comment=stringset[0].developer_comment,
                character_limit=stringset[0].character_limit,
            ),
        ]

        compiled = self.handler.compile(template, expected)
        self.assertEqual(compiled, expected_compilation)
