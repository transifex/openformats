import unittest
from io import open
from os import path

from openformats.exceptions import ParseError
from openformats.formats.yaml import YamlHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin


class YamlTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = YamlHandler
    TESTFILE_BASE = "openformats/tests/formats/yaml/files"

    def __init__(self, *args, **kwargs):
        super(YamlTestCase, self).__init__(*args, **kwargs)
        extra_files = ["1_en_exported.yml",
                       "1_en_exported_without_template.yml"]

        for fname in extra_files:
            filepath = path.join(self.TESTFILE_BASE, fname)
            with open(filepath, "r", encoding='utf-8') as myfile:
                self.data[fname[:-4]] = myfile.read()

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en_exported"])

    def test_compile_without_template(self):
        """Test that import-export is the same as the original file."""
        self.handler.should_use_template = False
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content,
                         self.data["1_en_exported_without_template"])

    def test_get_indent(self):
        template = "en:\n  foo: bar"
        self.assertEqual(self.handler._get_indent(template), 2)

        template = "en:\n\n  foo: bar"
        self.assertEqual(self.handler._get_indent(template), 2)

        template = "en:\n    foo: bar"
        self.assertEqual(self.handler._get_indent(template), 4)

        template = "en:\n\tfoo: bar"
        self.assertEqual(self.handler._get_indent(template), 4)

    def test_escape_dot(self):
        key = "abc.defg"
        self.assertEqual(self.handler.escape_dots(key), "abc<TX_DOT>defg")

        key = "abc"
        self.assertEqual(self.handler.escape_dots(key), key)

    def test_unescape_dot(self):
        key = "abc<TX_DOT>defg"
        self.assertEqual(self.handler.unescape_dots(key), "abc.defg")

        key = "abc"
        self.assertEqual(self.handler.unescape_dots(key), key)

    def test_wrap_yaml_dict(self):
        yaml_dict = {"foo": "bar"}
        self.assertDictEqual(self.handler._wrap_yaml_dict(yaml_dict),
                             yaml_dict)

        self.assertDictEqual(
            self.handler._wrap_yaml_dict(yaml_dict, "some_code"),
            {"some_code": yaml_dict}
        )

    def test_get_key_for_node(self):
        self.assertEqual(self.handler._get_key_for_node(1, ''), '<1>')

        self.assertEqual(self.handler._get_key_for_node(1, 'key1'), 'key1.<1>')

        self.assertEqual(self.handler._get_key_for_node('key.with.dots', ''),
                         'key<TX_DOT>with<TX_DOT>dots')

    def test_find_comment(self):
        content = ("no comment\n"
                   "# comment\n"
                   "# comment\n"
                   "no comment")
        start = 0
        end = len(content) - 1
        self.assertEqual(self.handler._find_comment(content, start, end),
                         "comment comment")

        content = ("no comment\n"
                   "no comment")
        start = 0
        end = len(content) - 1
        self.assertEqual(self.handler._find_comment(content, start, end), '')

    def test_write_styled_literal(self):
        string = OpenString('key', "a random string", flags="\"")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "\"a random string\"")

        string = OpenString('key', "a random string", flags="'")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "'a random string'")

        string = OpenString('key', "a random string", flags=">")
        self.assertEqual(self.handler._write_styled_literal(string),
                         ">-\n  a random string\n")

        string = OpenString('key', "a random string\nwith multiple lines\n",
                            flags="|")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "|\n  a random string\n  with multiple lines\n")

        string = OpenString('key', "a random string", flags="")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "a random string")

        string = OpenString('key', "a random string", flags=None)
        self.assertEqual(self.handler._write_styled_literal(string),
                         "a random string")

    # for covarage's sake
    def test_compile_pluralized(self):
        with self.assertRaises(NotImplementedError):
            self.handler._compile_pluralized('')

    def test_parse_pluralized_value(self):
        with self.assertRaises(NotImplementedError):
            self.handler.parse_pluralized_value('')

    def test_parse_invalid_yaml(self):
        invalid_content = "foo: bar\nwrong indentation"
        with self.assertRaises(ParseError):
            self.handler.parse(invalid_content)

    def test_openstring_attributes(self):
        content = "foo: bar\ntest: !tag 'content'"
        template, strings = self.handler.parse(content)

        test_string = strings[0]
        self.assertEqual(test_string.context, '')
        self.assertEqual(test_string.flags, '')

        content_string = strings[1]
        self.assertEqual(content_string.context, '!tag')
        self.assertEqual(content_string.flags, "'")
