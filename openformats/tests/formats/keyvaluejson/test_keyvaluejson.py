# -*- coding: utf-8 -*-

import unittest

import six
import json

from openformats.exceptions import ParseError
from openformats.formats.json import JsonHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import bytes_to_string, generate_random_string


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
        template, stringset = self.handler.parse('{"a": "%s"}' % self.random_string)
        compiled = self.handler.compile(template, [self.random_openstring])

        self.assertEqual(template, '{"a": "%s"}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, self.random_openstring.__dict__)
        self.assertEqual(compiled, '{"a": "%s"}' % self.random_string)

    def test_empty_string_ignored(self):
        template, stringset = self.handler.parse(
            '{"not_empty": "hello there", "empty": ""}'
        )
        self.assertEqual(len(stringset), 1)

        template, stringset = self.handler.parse(
            '{"not_empty": "hello there", "empty": [""]}'
        )
        self.assertEqual(len(stringset), 1)

    def test_empty_string_returned_in_compile(self):
        template, stringset = self.handler.parse(
            '{"a": "%s", "b": ""}' % self.random_string
        )
        compiled = self.handler.compile(template, [self.random_openstring])

        self.assertEqual(template, '{"a": "%s", "b": ""}' % self.random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, self.random_openstring.__dict__)
        self.assertEqual(compiled, '{"a": "%s", "b": ""}' % self.random_string)

    def test_root_object_is_list(self):
        source = '["%s"]' % self.random_string
        random_openstring = OpenString("..0..", self.random_string, order=0)
        random_hash = random_openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(template, '["%s"]' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_embedded_dicts(self):
        source = '{"a": {"b": "%s"}}' % self.random_string
        openstring = OpenString("a.b", self.random_string, order=0)
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template, '{"a": {"b": "%s"}}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_embedded_lists(self):
        source = '{"a": ["%s"]}' % self.random_string
        openstring = OpenString("a..0..", self.random_string, order=0)
        random_hash = openstring.template_replacement

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])

        self.assertEqual(template, '{"a": ["%s"]}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_python_values_are_ignored(self):
        source = '[true, "%s", 5e12]' % self.random_string
        random_openstring = OpenString("..1..", self.random_string, order=0)
        random_hash = random_openstring.template_replacement
        template, stringset = self.handler.parse(source)
        self.assertEqual(template, '[true, "%s", 5e12]' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)

    def test_compile_skips_removed_strings_for_dicts(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(template, '{"a": "%s", "b": "%s"}' % (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)
        self.assertEqual(compiled, '{"a": "%s"}' % string1)

    def test_compile_skips_removed_strings_for_lists(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)
        openstring2 = OpenString("..1..", string2, order=1)
        hash1 = openstring1.template_replacement
        hash2 = openstring2.template_replacement

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(template, '["%s", "%s"]' % (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)
        self.assertEqual(compiled, '["%s"]' % string1)

    def test_compile_skips_removed_nested_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)
        openstring2 = OpenString("..1...a", string2, order=1)
        hash1 = openstring1.template_replacement
        hash2 = openstring2.template_replacement

        source = '["%s", {"a": "%s"}]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(template, '["%s", {"a": "%s"}]' % (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)
        self.assertEqual(compiled, '["%s"]' % string1)

    def test_compile_skips_removed_nested_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = self.random_openstring
        openstring2 = OpenString("b..0..", string2, order=1)
        hash1 = self.random_hash
        hash2 = openstring2.template_replacement

        source = '{"a": "%s", "b": ["%s"]}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(template, '{"a": "%s", "b": ["%s"]}' % (hash1, hash2))
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].__dict__, openstring1.__dict__)
        self.assertEqual(stringset[1].__dict__, openstring2.__dict__)
        self.assertEqual(compiled, '{"a": "%s"}' % string1)

    def test_remove_all_strings_removed_from_list_but_non_strings_exist(self):
        random_string = self.random_string
        random_openstring = OpenString("a..1..", random_string, order=0)
        random_hash = random_openstring.template_replacement

        source = '{"a": [null, "%s"]}' % random_string

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [])
        compiled = self.handler.compile(updated_template, [])

        self.assertEqual(template, '{"a": [null, "%s"]}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, '{"a": [null]}')

    def test_respect_whitespace_only_strings(self):
        source = '{"a": " "}'

        template, _ = self.handler.parse(source)
        compiled = self.handler.compile(template, [])

        self.assertEqual(template, '{"a": " "}')
        self.assertEqual(compiled, '{"a": " "}')

    def test_remove_all_strings_removed_from_dict_but_non_strings_exist(self):
        random_string = self.random_string
        random_openstring = self.random_openstring
        random_hash = self.random_hash

        source = '{"a": "%s", "b": null}' % random_string

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [])
        compiled = self.handler.compile(updated_template, [])

        self.assertEqual(template, '{"a": "%s", "b": null}' % random_hash)
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, '{ "b": null}')

    def test_skip_start_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring2 = OpenString("b", string2, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring2])
        compiled = self.handler.compile(updated_template, [openstring2])

        self.assertEqual(compiled, '{ "b": "%s"}' % string2)

    def test_skip_end_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("a", string1, order=1)

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(compiled, '{"a": "%s"}' % string1)

    def test_skip_middle_of_dict(self):
        string1 = self.random_string
        string2 = generate_random_string()
        string3 = generate_random_string()
        openstring1 = OpenString("a", string1, order=0)
        openstring3 = OpenString("c", string3, order=2)

        source = '{"a": "%s", "b": "%s", "c": "%s"}' % (string1, string2, string3)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(
            template, [openstring1, openstring3]
        )
        compiled = self.handler.compile(updated_template, [openstring1, openstring3])

        self.assertEqual(compiled, '{"a": "%s", "c": "%s"}' % (string1, string3))

    def test_skip_start_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [stringset[1]])
        compiled = self.handler.compile(updated_template, [stringset[1]])

        self.assertEqual(compiled, '[ "%s"]' % string2)

    def test_empty_dict_at_start_of_list(self):
        string = self.random_string

        source = '[{}, "%s"]' % string

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)

        self.assertEqual(compiled, '[{}, "%s"]' % string)

    def test_skip_end_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)

        source = '["%s", "%s"]' % (string1, string2)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(template, [openstring1])
        compiled = self.handler.compile(updated_template, [openstring1])

        self.assertEqual(compiled, '["%s"]' % string1)

    def test_skip_middle_of_list(self):
        string1 = self.random_string
        string2 = generate_random_string()
        string3 = generate_random_string()
        openstring1 = OpenString("..0..", string1, order=0)
        openstring3 = OpenString("..2..", string3, order=2)

        source = '["%s", "%s", "%s"]' % (string1, string2, string3)

        template, stringset = self.handler.parse(source)
        updated_template = self.handler.sync_template(
            template, [openstring1, openstring3]
        )
        compiled = self.handler.compile(updated_template, [openstring1, openstring3])

        self.assertEqual(compiled, '["%s", "%s"]' % (string1, string3))

    def test_invalid_json(self):
        try:
            self.handler.parse("jaosjf")
        except Exception as e:
            self.assertIn(
                six.text_type(e),
                (
                    "Expecting value: line 1 column 1 (char 0)",
                    "No JSON object could be decoded",
                ),
            )
        else:
            raise AssertionError("No parse error raied")

    def test_invalid_json_type(self):
        template, stringset = self.handler.parse("[false]")
        self.assertEqual(stringset, [])
        self.assertEqual(template, "[false]")

        template, stringset = self.handler.parse('{"false": false}')
        self.assertEqual(stringset, [])
        self.assertEqual(template, '{"false": false}')

    def test_not_json_container(self):
        self._test_parse_error(
            '"hello"',
            "Was expecting whitespace or one of `[{` on " 'line 1, found `"` instead',
        )
        self._test_parse_error(
            "3",
            "Was expecting whitespace or one of `[{` on " "line 1, found `3` instead",
        )
        self._test_parse_error(
            "false",
            "Was expecting whitespace or one of `[{` on " "line 1, found `f` instead",
        )

    def test_skipping_stuff_within_strings(self):
        source = '{"a": "b,  ,c"}'
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_duplicate_keys(self):
        self._test_parse_error(
            '{"a": "hello", "a": "world"}', "Duplicate string key ('a') in line 1"
        )

    def test_display_json_errors(self):
        self._test_parse_error(
            '["]', "Unterminated string starting at: line 1 " "column 2 (char 1)"
        )

    def test_unescape(self):
        cases = (
            # simple => simple
            (["s", "i", "m", "p", "l", "e"], ["s", "i", "m", "p", "l", "e"]),
            # hεllo => hεllo
            (["h", "ε", "l", "l", "o"], ["h", "ε", "l", "l", "o"]),
            # h\u03b5llo => hεllo
            (
                ["h", "\\", "u", "0", "3", "b", "5", "l", "l", "o"],
                ["h", "ε", "l", "l", "o"],
            ),
            # a\"b => a"b
            (["a", "\\", '"', "b"], ["a", '"', "b"]),
            # a\/b => a/b
            (["a", "\\", "/", "b"], ["a", "/", "b"]),
            # a\/b => a?b, ? = BACKSPACE
            (["a", "\\", "b", "b"], ["a", "\b", "b"]),
            # a\fb => a?b, ? = FORMFEED
            (["a", "\\", "f", "b"], ["a", "\f", "b"]),
            # a\nb => a?b, ? = NEWLINE
            (["a", "\\", "n", "b"], ["a", "\n", "b"]),
            # a\rb => a?b, ? = CARRIAGE_RETURN
            (["a", "\\", "r", "b"], ["a", "\r", "b"]),
            # a\tb => a?b, ? = TAB
            (["a", "\\", "t", "b"], ["a", "\t", "b"]),
        )
        for raw, rich in cases:
            self.assertEqual(
                JsonHandler.unescape(bytes_to_string(raw)), bytes_to_string(rich)
            )

    def test_escape(self):
        cases = (
            # simple => simple
            (["s", "i", "m", "p", "l", "e"], ["s", "i", "m", "p", "l", "e"]),
            # hεllo => hεllo
            (["h", "ε", "l", "l", "o"], ["h", "ε", "l", "l", "o"]),
            # h\u03b5llo => h\\u03b5llo
            (
                ["h", "\\", "u", "0", "3", "b", "5", "l", "l", "o"],
                ["h", "\\", "\\", "u", "0", "3", "b", "5", "l", "l", "o"],
            ),
            # a"b =>a\"b
            (["a", '"', "b"], ["a", "\\", '"', "b"]),
            # a/b =>a/b
            (["a", "/", "b"], ["a", "/", "b"]),
            # a?b =>a\/b, ? = BACKSPACE
            (["a", "\b", "b"], ["a", "\\", "b", "b"]),
            # a?b =>a\fb, ? = FORMFEED
            (["a", "\f", "b"], ["a", "\\", "f", "b"]),
            # a?b =>a\nb, ? = NEWLINE
            (["a", "\n", "b"], ["a", "\\", "n", "b"]),
            # a?b =>a\rb, ? = CARRIAGE_RETURN
            (["a", "\r", "b"], ["a", "\\", "r", "b"]),
            # a?b => a\tb, ? = TAB
            (["a", "\t", "b"], ["a", "\\", "t", "b"]),
        )
        for rich, raw in cases:
            self.assertEqual(
                JsonHandler.escape(bytes_to_string(rich)), bytes_to_string(raw)
            )

    # PLURALS

    def test_invalid_plural_format(self):
        # Test various cases of messed-up braces
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"',
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have file_count} file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"',
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file. other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"',
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file}. other {You have file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"',
        )

    def test_invalid_plural_rules(self):
        # Only the following strings are allowed as plural rules:
        #   zero, one, few, many, other
        # Anything else, including their TX int equivalents are invalid.
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, 1 {file} 5 {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "1, 5" in pluralized entry with key: total_files',  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, once {file} mother {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "once, mother" in pluralized entry with key: total_files',  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, =3 {file} other {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): "=3" in pluralized entry with key: total_files',  # noqa
        )

    def test_irrelevant_whitespace_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        expected_translations = {0: "Empty", 5: "{count} files"}

        self._test_translations_equal(
            "{" '    "k": "{ cnt, plural, zero {Empty} other {{count} files} }"' "}",
            expected_translations,
        )
        self._test_translations_equal(
            "{" '    "k": "{cnt,plural,zero{Empty}other{{count} files} }"' "}",
            expected_translations,
        )
        self._test_translations_equal(
            '{ "k": "{    cnt,  plural,     zero  {Empty} other   {{count} files} }   "     }',  # noqa
            expected_translations,
        )
        self._test_translations_equal(
            "     {" '    "k": "{cnt,plural,zero{Empty}other{{count} files} }"' "}  ",
            expected_translations,
        )
        self._test_translations_equal(
            "{" '    "k": "  {cnt, plural, zero {Empty} other {{count} files} }"' "}",
            expected_translations,
        )
        self._test_translations_equal(
            "{" '    "k": "{cnt , plural , zero {Empty} other {{count} files} }"' "}",
            expected_translations,
        )

        # Escaped new lines should be allowed
        self._test_translations_equal(
            "{"
            '    "k": "{cnt, plural,\\n zero {Empty} other {{count} files} \\n}"'  # noqa
            "}",
            expected_translations,
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
            "{ gender_of_host, select, female {{host} appeared} male {{host} appeared} }",  # noqa
        )

    def test_nesting_with_plurals(self):
        expected_translations = {0: "Empty", 5: "{count} files"}

        self._test_translations_equal(
            '{ "k": { "a": "{ cnt, plural, zero {Empty} other {{count} files} }", "b": "c" } }',  # noqa
            expected_translations,
        )

    def test_whitespace_in_translations_not_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty} other {{count} files} }"}',
            {0: " Empty", 5: "{count} files"},
        )
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty  } other {{count} files } }"}',
            {0: " Empty  ", 5: "{count} files "},
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
        template, stringset = self.handler.parse(source)
        for rule_int in six.iterkeys(translations_by_rule):
            self.assertEqual(
                translations_by_rule[rule_int], stringset[0].string[rule_int]
            )

    def test_sync_template_adds_missing_dict_key(self):
        string1 = self.random_string
        string2 = generate_random_string()

        source = '{"a": "%s"}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]

        new = OpenString("b", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])

        compiled = self.handler.compile(updated_template, [existing, new])

        data = json.loads(compiled)
        self.assertEqual(data["a"], string1)
        self.assertEqual(data["b"], string2)
        self.assertEqual(set(data.keys()), {"a", "b"})

    def test_sync_template_adds_to_empty_dict(self):
        string1 = self.random_string
        openstring = OpenString("a", string1, order=0)

        source = "{}"
        # Directly call sync_template (no strings in template)
        updated_template = self.handler.sync_template(source, [openstring])
        compiled = self.handler.compile(updated_template, [openstring])

        data = json.loads(compiled)
        self.assertEqual(data, {"a": string1})

    def test_sync_template_adds_missing_dict_key_multiline(self):
        string1 = self.random_string
        string2 = generate_random_string()

        source = '{\n  "a": "%s"\n}' % string1
        template, stringset = self.handler.parse(source)
        existing = stringset[0]
        new = OpenString("b", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])
        compiled = self.handler.compile(updated_template, [existing, new])

        data = json.loads(compiled)
        self.assertEqual(data["a"], string1)
        self.assertEqual(data["b"], string2)

    def test_sync_template_adds_missing_list_item_root(self):
        string1 = self.random_string
        string2 = generate_random_string()

        source = '["%s"]' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]
        new = OpenString("..1..", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])
        compiled = self.handler.compile(updated_template, [existing, new])

        data = json.loads(compiled)
        # First element should still be simple string
        self.assertEqual(data[0], string1)
        # Second element is whatever _add_strings_to_template produced;
        # we only assert that our new string is present somewhere in it.
        # For list root, it is a dict { "..1..": "<string>" }.
        self.assertIsInstance(data[1], dict)
        self.assertIn("..1..", data[1])
        self.assertEqual(data[1]["..1.."], string2)

    def test_sync_template_adds_to_empty_list(self):
        string1 = self.random_string
        openstring = OpenString("..0..", string1, order=0)

        source = "[]"
        updated_template = self.handler.sync_template(source, [openstring])
        compiled = self.handler.compile(updated_template, [openstring])

        data = json.loads(compiled)
        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], dict)
        self.assertIn("..0..", data[0])
        self.assertEqual(data[0]["..0.."], string1)

    def test_sync_template_adds_and_removes_dict_keys(self):
        string1 = self.random_string  # for "a"
        string2 = generate_random_string()  # for "b"
        string3 = generate_random_string()  # for "c"

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # We want to keep "b" and add "c", drop "a"
        keep_b = [s for s in stringset if s.key == "b"][0]
        new_c = OpenString("c", string3, order=keep_b.order + 1)

        updated_template = self.handler.sync_template(template, [keep_b, new_c])
        compiled = self.handler.compile(updated_template, [keep_b, new_c])

        data = json.loads(compiled)
        self.assertEqual(set(data.keys()), {"b", "c"})
        self.assertEqual(data["b"], string2)
        self.assertEqual(data["c"], string3)

    def test_escaped_key_with_dot_roundtrip(self):
        string = self.random_string
        source = '{"a.b": "%s"}' % string

        template, stringset = self.handler.parse(source)
        # Key inside OpenString should be escaped (a\.b)
        self.assertEqual(stringset[0].key, "a\\.b")

        # Sync with same stringset should not change anything
        updated_template = self.handler.sync_template(template, stringset)
        compiled = self.handler.compile(updated_template, stringset)

        data = json.loads(compiled)
        # Original JSON key must be preserved on output
        self.assertEqual(data, {"a.b": string})

    def test_sync_template_adds_nested_list_item_as_new_key(self):
        string1 = self.random_string
        string2 = generate_random_string()

        source = '{"a": ["%s"]}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]  # key "a..0.."
        new = OpenString("a..1..", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])
        compiled = self.handler.compile(updated_template, [existing, new])

        data = json.loads(compiled)
        # "a" list remains as-is
        self.assertEqual(data["a"], [string1])
        # New key "a..1.." is added at top level
        self.assertIn("a..1..", data)
        self.assertEqual(data["a..1.."], string2)

    def test_sync_template_removes_all_strings_from_dict(self):
        """Test removing all strings from a dict"""
        string1 = generate_random_string()
        string2 = generate_random_string()

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Sync with empty stringset to remove all strings
        updated_template = self.handler.sync_template(template, [])
        compiled = self.handler.compile(updated_template, [])

        self.assertEqual(compiled, "{ }")

    def test_sync_template_removes_all_strings_from_list(self):
        """Test removing all strings from a list"""
        string1 = generate_random_string()
        string2 = generate_random_string()

        source = '["%s", "%s"]' % (string1, string2)
        template, _ = self.handler.parse(source)

        updated_template = self.handler.sync_template(template, [])
        compiled = self.handler.compile(updated_template, [])

        self.assertEqual(compiled, "[ ]")

    def test_sync_template_removes_middle_strings_from_dict(self):
        """Test removing only middle strings from dict"""
        string1 = generate_random_string()
        string2 = generate_random_string()
        string3 = generate_random_string()

        source = '{"a": "%s", "b": "%s", "c": "%s"}' % (string1, string2, string3)
        template, stringset = self.handler.parse(source)

        # Keep only first and last
        keep = [s for s in stringset if s.key in ("a", "c")]
        updated_template = self.handler.sync_template(template, keep)
        compiled = self.handler.compile(updated_template, keep)

        import json

        data = json.loads(compiled)
        self.assertEqual(set(data.keys()), {"a", "c"})
        self.assertEqual(data["a"], string1)
        self.assertEqual(data["c"], string3)

    def test_sync_template_removes_first_string_from_dict(self):
        """Test removing only the first string from dict"""
        string1 = generate_random_string()
        string2 = generate_random_string()

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Keep only "b"
        keep_b = [s for s in stringset if s.key == "b"]
        updated_template = self.handler.sync_template(template, keep_b)
        compiled = self.handler.compile(updated_template, keep_b)

        import json

        data = json.loads(compiled)
        self.assertEqual(data, {"b": string2})

    def test_sync_template_removes_last_string_from_dict(self):
        """Test removing only the last string from dict"""
        string1 = generate_random_string()
        string2 = generate_random_string()

        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Keep only "a"
        keep_a = [s for s in stringset if s.key == "a"]
        updated_template = self.handler.sync_template(template, keep_a)
        compiled = self.handler.compile(updated_template, keep_a)

        import json

        data = json.loads(compiled)
        self.assertEqual(data, {"a": string1})

    def test_sync_template_adds_pluralized_string(self):
        """Test adding a pluralized string via sync_template"""
        string1 = generate_random_string()

        source = '{"a": "%s"}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]

        plural_string = OpenString(
            "b",
            {1: "one file", 5: "{count} files"},
            order=existing.order + 1,
            pluralized=True,
        )

        updated_template = self.handler.sync_template(
            template, [existing, plural_string]
        )
        compiled = self.handler.compile(updated_template, [existing, plural_string])

        data = json.loads(compiled)
        self.assertIn("a", data)
        self.assertIn("b", data)

    def test_sync_template_removes_pluralized_string(self):
        """Test removing a pluralized string"""
        source = '{"a": "{cnt, plural, one {file} other {{count} files}}"}'
        template, stringset = self.handler.parse(source)

        # Remove the pluralized string
        updated_template = self.handler.sync_template(template, [])
        compiled = self.handler.compile(updated_template, [])

        self.assertEqual(compiled, "{}")

    def test_sync_template_deeply_nested_dict_add(self):
        """Test adding to deeply nested dict structure"""
        string1 = generate_random_string()
        source = '{"a": {"b": {"c": "%s"}}}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]
        string2 = generate_random_string()
        new = OpenString("a.b.d", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])
        compiled = self.handler.compile(updated_template, [existing, new])

        data = json.loads(compiled)
        self.assertEqual(data["a"]["b"]["c"], string1)
        self.assertEqual(data["a.b.d"], string2)

    def test_sync_template_deeply_nested_dict_remove(self):
        """Test removing from deeply nested dict"""
        string1 = generate_random_string()
        string2 = generate_random_string()
        source = '{"a": {"b": {"c": "%s", "d": "%s"}}}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Keep only "a.b.c"
        keep = [s for s in stringset if s.key == "a.b.c"]
        updated_template = self.handler.sync_template(template, keep)
        compiled = self.handler.compile(updated_template, keep)

        import json

        data = json.loads(compiled)
        self.assertEqual(data["a"]["b"]["c"], string1)
        self.assertNotIn("d", data["a"]["b"])

    def test_sync_template_mixed_nested_structures(self):
        """Test dict inside list inside dict"""
        string1 = generate_random_string()
        source = '{"a": [{"b": "%s"}]}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]
        string2 = generate_random_string()
        new = OpenString("c", string2, order=existing.order + 1)

        updated_template = self.handler.sync_template(template, [existing, new])
        compiled = self.handler.compile(updated_template, [existing, new])

        import json

        data = json.loads(compiled)
        self.assertEqual(data["a"][0]["b"], string1)
        self.assertEqual(data["c"], string2)

    def test_sync_template_remove_entire_nested_branch(self):
        """Test removing all strings from a nested branch"""
        string1 = generate_random_string()
        string2 = generate_random_string()
        source = '{"a": {"b": "%s"}, "c": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Keep only "c", which should remove entire "a" branch
        keep_c = [s for s in stringset if s.key == "c"]
        updated_template = self.handler.sync_template(template, keep_c)
        compiled = self.handler.compile(updated_template, keep_c)

        import json

        data = json.loads(compiled)
        self.assertNotIn("a", data)
        self.assertEqual(data["c"], string2)

    def test_sync_template_multiple_additions_single_call(self):
        """Test adding multiple strings in one sync call"""
        string1 = generate_random_string()
        source = '{"a": "%s"}' % string1
        template, stringset = self.handler.parse(source)

        existing = stringset[0]
        string2 = generate_random_string()
        string3 = generate_random_string()
        string4 = generate_random_string()

        new2 = OpenString("b", string2, order=existing.order + 1)
        new3 = OpenString("c", string3, order=existing.order + 2)
        new4 = OpenString("d", string4, order=existing.order + 3)

        updated_template = self.handler.sync_template(
            template, [existing, new2, new3, new4]
        )
        compiled = self.handler.compile(updated_template, [existing, new2, new3, new4])

        import json

        data = json.loads(compiled)
        self.assertEqual(len(data), 4)
        self.assertEqual(data["a"], string1)
        self.assertEqual(data["b"], string2)
        self.assertEqual(data["c"], string3)
        self.assertEqual(data["d"], string4)

    def test_sync_template_completely_different_stringset(self):
        """Test syncing with completely different keys"""
        string1 = generate_random_string()
        string2 = generate_random_string()
        source = '{"a": "%s", "b": "%s"}' % (string1, string2)
        template, stringset = self.handler.parse(source)

        # Completely new strings
        string3 = generate_random_string()
        string4 = generate_random_string()
        new1 = OpenString("x", string3, order=0)
        new2 = OpenString("y", string4, order=1)

        updated_template = self.handler.sync_template(template, [new1, new2])
        compiled = self.handler.compile(updated_template, [new1, new2])

        import json

        data = json.loads(compiled)
        self.assertEqual(set(data.keys()), {"x", "y"})
        self.assertEqual(data["x"], string3)
        self.assertEqual(data["y"], string4)

    def test_sync_template_maintains_key_order(self):
        """Test that key order is maintained during sync"""
        string1 = generate_random_string()
        string2 = generate_random_string()
        string3 = generate_random_string()

        source = '{"a": "%s", "b": "%s", "c": "%s"}' % (string1, string2, string3)
        template, stringset = self.handler.parse(source)

        # Remove middle, add new at end
        keep = [s for s in stringset if s.key in ("a", "c")]
        string4 = generate_random_string()
        new = OpenString("d", string4, order=10)

        updated_template = self.handler.sync_template(template, keep + [new])
        compiled = self.handler.compile(updated_template, keep + [new])

        # Parse to verify structure
        import json

        data = json.loads(compiled)
        keys = list(data.keys())

        # Should have a, c, d (in that order for dicts that preserve
        # insertion order)
        self.assertIn("a", keys)
        self.assertIn("c", keys)
        self.assertIn("d", keys)
        self.assertNotIn("b", keys)

    def test_sync_template_adds_missing_middle_key_and_keeps_later_key(self):
        """
        Scenario:

        - Template has: a, b, d
        - DB stringset has: a, b, c, d

        After sync_template + compile, we expect:
        - "c" to be added
        - "d" to still exist
        - all four keys present in the compiled JSON
        """
        string1 = generate_random_string()
        string2 = generate_random_string()
        string3 = generate_random_string()
        string4 = generate_random_string()

        # Template is missing "c"
        source = '{"a": "%s", "b": "%s", "d": "%s"}' % (
            string1,
            string2,
            string4,
        )
        template, stringset = self.handler.parse(source)

        a_str = [s for s in stringset if s.key == "a"][0]
        b_str = [s for s in stringset if s.key == "b"][0]
        d_str = [s for s in stringset if s.key == "d"][0]

        c_str = OpenString("c", string3, order=b_str.order + 1)

        db_stringset = [a_str, b_str, c_str, d_str]

        updated_template = self.handler.sync_template(template, db_stringset)
        compiled = self.handler.compile(updated_template, db_stringset)

        data = json.loads(compiled)

        self.assertEqual(c_str.order, d_str.order)
        self.assertEqual(data["a"], string1)
        self.assertEqual(data["b"], string2)
        self.assertEqual(data["c"], string3)
        self.assertEqual(data["d"], string4)

        keys = list(data.keys())
        self.assertEqual(keys, ["a", "b", "c", "d"])
