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
        self.handler.key_indent_map = {}
        string = OpenString('key', "a random string", flags="\"")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "\"a random string\"")

        string = OpenString('key', "a random string", flags="'")
        self.assertEqual(self.handler._write_styled_literal(string),
                         "'a random string'")

        string = OpenString('key', "a random string", flags=">")
        self.assertEqual(self.handler._write_styled_literal(string),
                         ">-\n  a random string\n")

        string = OpenString('key.[0]', "a random string\nwith multiple lines\n",
                            flags="|")
        template = '---\ntitle: 6391362253bdac99fff7bf50ff014be3_tr\nmdBody:\n\n  - 5b269595654e5f2059ec52043a54b454_tr'
        self.assertEqual(self.handler._write_styled_literal(string, template, 60),
                         "|\n    a random string\n    with multiple lines\n")

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

    def test_parse_duplicate_keys(self):
        content = '''\
            something:
              attribute_1: Attribute 1 value
              attribute_2: Attribute 2 value
              attribute_3: Attribute 3 value
              attribute_1: Attribute 1 value
              attribute_2: Attribute 2 value
        '''

        with self.assertRaises(ParseError) as e:
            self.handler.parse(content)

        self.assertTrue(
            str(e.exception) in [
                "Duplicate keys found (attribute_2, attribute_1)",
                "Duplicate keys found (attribute_1, attribute_2)",
            ]
        )

    def test_parse_anchor_with_label_is_maintained_on_template(self):
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual("&another_anchor    " in remade_orig_content, True)

    def full_run(self, source, translation, expected):
        """ Parse source, replace first extracted string, recompile and compare
            against expected output.
        """

        template, stringset = self.handler.parse(source)
        stringset[0]._strings[5] = translation
        self.assertEqual(self.handler.compile(template, stringset), expected)

    def test_block_folding(self):
        # a: >
        #   b
        # c:
        #   d
        source = '\n'.join(["a: >",
                            "  b",
                            "c:",
                            "  d"]) + "\n"

        # Translation same as extracted source string
        self.full_run(source, "b\n", source)

        # Translation without newline, compiler uses line folding
        self.full_run(source,
                      "b",
                      '\n'.join(["a: >-",
                                 "  b",
                                 "c:",
                                 "  d"]) + "\n")

        # Translation with space, compiler uses line folding and appends space
        self.full_run(source,
                      "b ",
                      '\n'.join(["a: >-",
                                 "  b ",
                                 "c:",
                                 "  d"]) + "\n")

    def test_line_folding(self):
        # a: >-
        #   b
        # c:
        #   d
        source = '\n'.join(["a: >-",
                            "  b",
                            "c:",
                            "  d"]) + "\n"

        # Translation same as extracted source string
        self.full_run(source, "b", source)

        # Translation with newline, compiler uses block folding
        self.full_run(source,
                      "b\n",
                      '\n'.join(["a: >",
                                 "  b",
                                 "c:",
                                 "  d"]) + "\n")

        # Translation with space, compiler uses line folding and appends space
        self.full_run(source,
                      "b ",
                      '\n'.join(["a: >-",
                                 "  b ",
                                 "c:",
                                 "  d"]) + "\n")

    def test_parse_empty_anchor(self):
        source = (u"key1: value1\n"
                  u"key2: &anchor2 value2\n"
                  u"key3: &anchor3")
        template, stringset = self.handler.parse(source)

        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].string, u"value1")
        self.assertEqual(stringset[1].string, u"value2")

        expected_template = (u"key1: {}\n"
                             u"key2: &anchor2 {}\n"
                             u"key3: &anchor3".
                             format(stringset[0].template_replacement,
                                    stringset[1].template_replacement))
        self.assertEqual(expected_template, template)
        self.assertEqual(self.handler.compile(template, stringset), source)
