# -*- coding: utf-8 -*-

import unittest
import json
import six

from openformats.formats.json import StructuredJsonHandler

from openformats.exceptions import ParseError
from openformats.strings import OpenString
from openformats.utils.json import DumbJson
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

    def test_broken(self):
        stringset = [
            OpenString("b", "foo_tr", order=0)
        ]
        string_hash = stringset[0].template_replacement
        template, stringset = self.handler.parse('{"a": {"string":" ", "character_limit": 1, "developer_comment": "A"}, "b": {"string": "foo"}}') # noqa
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(template, '{"a": {"string":" ", "character_limit": 1, "developer_comment": "A"}, "b": {"string": "%s"}}' % string_hash) # noqa
        self.assertEqual(compiled, '{"a": {"string":" ", "character_limit": 1, "developer_comment": "A"}, "b": {"string": "foo"}}') # noqa

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
        self._test_parse_error('[false]', "No strings could be extracted")

        self._test_parse_error('{"false": false}', "No strings could be extracted")

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

    def test_invalid_structured_json_value(self):
        self._test_parse_error(
            '{"key": {"string": {"test": {"string": "test"}}}}',
            "Invalid string value in line 1"
        )

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

    def test_empty_strings(self):
        source = u"""
        {
            "a": {
                "string": ""
            },
            "b": {
                "string": "",
                "character_limit": 35
            }
        }
        """
        self._test_parse_error(
            source,
            "No strings could be extracted"
        )

    def test_empty_values_with_null_template_value(self):
        source = u"""
        {
            "a" : {
                "developer_comment" : null,
                "string" : "str",
                "context" : null
            }
        }
        """

        expected_compilation = u"""
        {
            "a" : {
                "developer_comment" : null,
                "string" : "str",
                "context" : null
            }
        }
        """

        template, stringset = self.handler.parse(source)

        expected = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context="",
                developer_comment="",
                character_limit=stringset[0].character_limit,
            ),
        ]

        compiled = self.handler.compile(template, expected)
        self.assertEqual(compiled, expected_compilation)

    def test_empty_values_with_empty_template_value(self):
        source = u"""
        {
            "a" : {
                "developer_comment" : "",
                "string" : "str",
                "context" : ""
            }
        }
        """

        expected_compilation = u"""
        {
            "a" : {
                "developer_comment" : "",
                "string" : "str",
                "context" : ""
            }
        }
        """

        template, stringset = self.handler.parse(source)

        expected = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context="",
                developer_comment="",
                character_limit=stringset[0].character_limit,
            ),
        ]

        compiled = self.handler.compile(template, expected)
        self.assertEqual(compiled, expected_compilation)

    def test_non_empty_values_with_null_template_value(self):
        source = u"""
        {
            "a" : {
                "developer_comment" : null,
                "string" : "str",
                "context" : null
            }
        }
        """

        expected_compilation = u"""
        {
            "a" : {
                "developer_comment" : "some_comment",
                "string" : "str",
                "context" : "some_context"
            }
        }
        """

        template, stringset = self.handler.parse(source)

        expected = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context="some_context",
                developer_comment="some_comment",
                character_limit=stringset[0].character_limit,
            ),
        ]

        compiled = self.handler.compile(template, expected)
        self.assertEqual(compiled, expected_compilation)

    def test_non_empty_values_with_non_existing_template_value(self):
        source = u"""
        {
            "a" : {
                "string" : "str"
            }
        }
        """

        expected_compilation = u"""
        {
            "a" : {
                "string" : "str",
                "context" : "some_context",
                "developer_comment" : "some_comment"
            }
        }
        """

        template, stringset = self.handler.parse(source)

        expected = [
            OpenString(
                key=stringset[0].key,
                string_or_strings=stringset[0].string,
                context="some_context",
                developer_comment="some_comment",
                character_limit=stringset[0].character_limit,
            ),
        ]

        compiled = self.handler.compile(template, expected)
        self.assertEqual(compiled, expected_compilation)

    def test_sync_template_all_structured_deleted_dict_root(self):
        # Dict root with only structured entries
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '{"a": {"string": "%s"}, "b": {"string": "%s"}}' % (s1, s2)

        template, _ = self.handler.parse(source)

        # Empty stringset -> all structured entries should be removed
        updated = self.handler.sync_template(template, [])

        data = json.loads(updated)
        # Dict root should become an empty object
        self.assertEqual(data, {})

    def test_sync_template_all_structured_deleted_list_root(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '[{"a": {"string": "%s"}, "b": {"string": "%s"}}]' % (s1, s2)

        template, _ = self.handler.parse(source)

        updated = self.handler.sync_template(template, [])

        data = json.loads(updated)
        self.assertEqual(data, [])


    def test_sync_template_keeps_all_when_strings_match(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '{"a": {"string": "%s"}, "b": {"string": "%s"}}' % (s1, s2)

        template, stringset = self.handler.parse(source)

        hash1 = stringset[0].template_replacement
        hash2 = stringset[1].template_replacement
        self.assertIn(hash1, template)
        self.assertIn(hash2, template)

        updated = self.handler.sync_template(template, stringset)

        self.assertEqual(updated, template)

    def test_sync_template_removes_missing_string_for_dict_root(self):
        # Two strings, but we "forget" one in stringset -> should be removed
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '{"a": {"string": "%s"}, "b": {"string": "%s"}}' % (s1, s2)

        template, stringset = self.handler.parse(source)
        _, os_b = stringset

        # Keep only b
        new_stringset = [os_b]
        updated = self.handler.sync_template(template, new_stringset)

        # Updated template should only contain "b" with its hash
        hash_b = os_b.template_replacement
        data = json.loads(updated)
        self.assertEqual(set(data.keys()), {"b"})
        self.assertEqual(data["b"]["string"], hash_b)

    def test_sync_template_adds_new_string_for_dict_root(self):
        # Start with only "a" in template; add "b" via sync_template
        s1 = generate_random_string()
        source = '{"a": {"string": "%s"}}' % s1

        template, stringset = self.handler.parse(source)
        os_a = stringset[0]

        # Create a new OpenString "b" that does not exist in template
        s2 = generate_random_string()
        os_b = OpenString("b", s2, order=1)
        hash_b = os_b.template_replacement

        updated = self.handler.sync_template(template, [os_a, os_b])

        data = json.loads(updated)
        # Both keys should be present
        self.assertEqual(set(data.keys()), {"a", "b"})
        # "b" should be a structured entry with "string" == hash
        self.assertIsInstance(data["b"], dict)
        self.assertEqual(data["b"]["string"], hash_b)

    def test_sync_template_list_root_remove(self):
        # Root is a list; inner object is the structured container
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '[{"a": {"string": "%s"}, "b": {"string": "%s"}}]' % (s1, s2)

        template, stringset = self.handler.parse(source)
        os_a, _ = stringset

        # Keep only "a"
        updated = self.handler.sync_template(template, [os_a])

        data = json.loads(updated)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        inner = data[0]
        self.assertEqual(set(inner.keys()), {"a"})
        self.assertEqual(inner["a"]["string"], os_a.template_replacement)


    def test_get_root_for_dict_and_list(self):
        # Dict root
        s = generate_random_string()
        source_dict = '{"a": {"string": "%s"}}' % s
        parsed_dict = DumbJson(source_dict)
        root_type_dict = self.handler._get_root(parsed_dict)
        self.assertEqual(root_type_dict, dict)

        # List root with inner dict
        source_list = '[{"a": {"string": "%s"}}]' % s
        parsed_list = DumbJson(source_list)
        root_type_list = self.handler._get_root(parsed_list)
        self.assertEqual(root_type_list, list)

        # List root with no dict elements -> should return list, list
        parsed_list2 = DumbJson('[1, 2, 3]')
        root_type2 = self.handler._get_root(parsed_list2)
        self.assertEqual(root_type2, list)

    def test_make_added_entry_structure(self):
        os = OpenString(
            "new_key",
            "dummy",
            order=0,
            context="ctx",
            developer_comment="dev_comment",
            character_limit=42,
        )
        entry = self.handler._make_added_entry_for_dict(os)

        # Wrap in braces so json.loads can parse it as a dict
        wrapped = "{%s}" % entry
        data = json.loads(wrapped)

        self.assertIn("new_key", data)
        payload = data["new_key"]
        self.assertEqual(payload["string"], os.template_replacement)
        self.assertEqual(payload["context"], "ctx")
        self.assertEqual(payload["developer_comment"], "dev_comment")
        self.assertEqual(payload["character_limit"], 42)

    def test_sync_template_keeps_non_structured_values_and_lists(self):
        # a, b are structured; c is primitive; d is list
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = """
        {
            "a": { "string": "%s" },
            "b": { "string": "%s" },
            "c": 123,
            "d": [1, 2, 3]
        }
        """ % (s1, s2)

        template, stringset = self.handler.parse(source)
        os_a, os_b = stringset

        # Keep only "a" -> "b" should be removed, "c" and "d" should remain
        updated = self.handler.sync_template(template, [os_a])

        data = json.loads(updated)
        self.assertEqual(set(data.keys()), {"a", "c", "d"})
        self.assertEqual(data["c"], 123)
        self.assertEqual(data["d"], [1, 2, 3])
        self.assertEqual(data["a"]["string"], os_a.template_replacement)

    def test_sync_template_prunes_empty_nested_containers(self):
        # a.x and a.y are structured; b.z is structured
        s1 = generate_random_string()
        s2 = generate_random_string()
        s3 = generate_random_string()
        source = """
        {
            "a": {
                "x": { "string": "%s" },
                "y": { "string": "%s" }
            },
            "b": {
                "z": { "string": "%s" }
            }
        }
        """ % (s1, s2, s3)

        template, stringset = self.handler.parse(source)
        os_ax, os_ay, os_bz = stringset

        # Keep only "b.z" -> "a" should be completely pruned
        updated = self.handler.sync_template(template, [os_bz])

        data = json.loads(updated)
        self.assertEqual(set(data.keys()), {"b"})
        self.assertIn("z", data["b"])
        self.assertEqual(data["b"]["z"]["string"], os_bz.template_replacement)

    def test_sync_template_keeps_container_if_any_child_kept(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = """
        {
            "group": {
                "keep_me":   { "string": "%s" },
                "drop_me":   { "string": "%s" }
            }
        }
        """ % (s1, s2)

        template, stringset = self.handler.parse(source)
        os_keep, _ = stringset

        updated = self.handler.sync_template(template, [os_keep])

        data = json.loads(updated)
        self.assertEqual(set(data.keys()), {"group"})
        group = data["group"]
        self.assertEqual(set(group.keys()), {"keep_me"})
        self.assertEqual(
            group["keep_me"]["string"],
            os_keep.template_replacement,
        )

    def test_sync_template_plural_hash_matching(self):
        plural_source = '{ cnt, plural, one {one} other {many} }'
        source = '{"k": {"string": "%s"}}' % plural_source

        template, stringset = self.handler.parse(source)
        os = stringset[0]
        hash_val = os.template_replacement

        # Sanity: template should contain the hash inside the ICU string
        self.assertIn(hash_val, template)

        # Keeping the same OpenString should keep the entry
        updated = self.handler.sync_template(template, [os])
        data = json.loads(updated)
        self.assertIn("k", data)
        self.assertIn(hash_val, data["k"]["string"])

    def test_sync_template_list_root_with_non_dict_siblings(self):
        s1 = generate_random_string()
        s2 = generate_random_string()

        source = """
        [
            {
                "a": { "string": "%s" },
                "b": { "string": "%s" }
            },
            123,
            456
        ]
        """ % (s1, s2)

        template, stringset = self.handler.parse(source)
        os_a, os_b = stringset

        # Keep only "a"
        updated = self.handler.sync_template(template, [os_a])

        data = json.loads(updated)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)

        inner = data[0]
        self.assertEqual(set(inner.keys()), {"a"})
        self.assertEqual(inner["a"]["string"], os_a.template_replacement)

        # non-dict siblings unchanged
        self.assertEqual(data[1], 123)
        self.assertEqual(data[2], 456)

    def test_sync_template_with_empty_stringset_removes_all_structured_entries(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = """
        {
            "a": { "string": "%s" },
            "b": { "string": "%s" },
            "meta": "keep_me"
        }
        """ % (s1, s2)

        template, _ = self.handler.parse(source)

        updated = self.handler.sync_template(template, [])

        data = json.loads(updated)
        # Only non-structured stuff should remain
        self.assertEqual(set(data.keys()), {"meta"})
        self.assertEqual(data["meta"], "keep_me")

    def test_sync_template_seen_keys_matches_kept_entries(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        source = '{"a": {"string": "%s"}, "b": {"string": "%s"}}' % (s1, s2)

        template, stringset = self.handler.parse(source)
        os_a, _ = stringset

        updated = self.handler.sync_template(template, [os_a])

        data = json.loads(updated)
        self.assertEqual(set(data.keys()), {"a"})

    def test_sync_template_replaces_d_with_c(self):
        s1 = generate_random_string()
        s2 = generate_random_string()
        s3 = generate_random_string()

        source = json.dumps({
            "a": {"string": s1},
            "b": {"string": s2},
            "d": {"string": "old_d"},
        })
        template, stringset = self.handler.parse(source)

        # stringset contains a, b, d — now replace the last with c
        os_a, os_b, os_d = stringset
        os_c = OpenString("c", s3, order=os_d.order)

        updated = self.handler.sync_template(
            template,
            [os_a, os_b, os_c, os_d],
        )
        data = json.loads(updated)

        self.assertEqual(set(data.keys()), {"a", "b", "c", "d"})
        self.assertEqual(data["a"]["string"], os_a.template_replacement)
        self.assertEqual(data["b"]["string"], os_b.template_replacement)
        self.assertEqual(data["c"]["string"], os_c.template_replacement)
        self.assertEqual(data["d"]["string"], os_d.template_replacement)
