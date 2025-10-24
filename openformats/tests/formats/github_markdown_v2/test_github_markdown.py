# -*- coding: utf-8 -*-
import unittest
from io import open
from os import path

import six

from openformats.formats.github_markdown_v2 import GithubMarkdownHandlerV2
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin

unittest.TestCase.maxDiff = None


class GithubMarkdownV2TestCase(CommonFormatTestMixin, unittest.TestCase):
    """Tests the basic functionality of GithubMarkdownHandlerV2."""
    HANDLER_CLASS = GithubMarkdownHandlerV2
    TESTFILE_BASE = "openformats/tests/formats/github_markdown_v2/files"

    def __init__(self, *args, **kwargs):
        super(GithubMarkdownV2TestCase, self).__init__(*args, **kwargs)
        filepath = path.join(self.TESTFILE_BASE, "1_en_export.md")
        with open(filepath, "r", encoding='utf-8') as myfile:
            self.data['1_en_export'] = myfile.read()

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en_export"])

    def test_parse(self):
        """Test parse converts tabs to spaces"""
        content_with_tab = self.handler.parse(content=u"# foo	bar")
        content_with_spaces = self.handler.parse(content=u"# foo    bar")
        self.assertEqual(content_with_tab[0], content_with_spaces[0])

    def test_parse_non_unicode(self):
        """Test parse converts tabs to spaces"""
        content_with_non_unicode_space = self.handler.parse(content=u"# foo\xa0bar")
        content_with_normal_space = self.handler.parse(content=u"# foo bar")
        self.assertEqual(
            content_with_non_unicode_space[0], content_with_normal_space[0])
        
    def test_parse_indented_note_block(self):
        indent_content = u"""
Sample heading

> [!NOTE]
> Non-indented block

1. Sample heading

    Sample sub-heading

    > [!NOTE]
    > This is an indented block
"""
        expected_hashed_template = (
            "\n9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr"
            "\n\n3afcdbfeb6ecfbdd0ba628696e3cc163_tr\n\n"
            "1. 247730f9d0d2eaad265a470e32aa0cdf_tr\n\n"
            "   cdee9bf40a070d58d14dfa3bb61e0032_tr\n\n"
            "    7693e302dc09b57483d26522ef25feb4_tr\n"
        )
        parsed_content_indent = self.handler.parse(content=indent_content)

        self.assertEqual(parsed_content_indent[0], expected_hashed_template)
        self.assertEqual(len(parsed_content_indent[1]), 5)

        self.assertEqual(parsed_content_indent[1][0].string, "Sample heading")
        self.assertEqual(
            parsed_content_indent[1][1].string, "> [!NOTE]\n> Non-indented block"
        )
        self.assertEqual(parsed_content_indent[1][2].string, "Sample heading")
        self.assertEqual(parsed_content_indent[1][3].string, " Sample sub-heading")
        self.assertEqual(
            parsed_content_indent[1][4].string, 
            " > [!NOTE]\n > This is an indented block"
        )

    def test_parse_indented_code_block_with_tabs(self):
        tabbed_indent_content = u"""
Sample heading

> [!NOTE]
> Non-indented block

1. Sample heading

\tSample sub-heading

\t> [!NOTE]
\t> This is an indented block
"""
        expected_hashed_template = (
            "\n9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr"
            "\n\n3afcdbfeb6ecfbdd0ba628696e3cc163_tr\n\n"
            "1. 247730f9d0d2eaad265a470e32aa0cdf_tr\n\n"
            "   cdee9bf40a070d58d14dfa3bb61e0032_tr\n\n"
            "    7693e302dc09b57483d26522ef25feb4_tr\n"
        )
        parsed_content_tabbed_indent = self.handler.parse(
            content=tabbed_indent_content
        )

        self.assertEqual(parsed_content_tabbed_indent[0], expected_hashed_template)
        self.assertEqual(len(parsed_content_tabbed_indent[1]), 5)

        self.assertEqual(parsed_content_tabbed_indent[1][0].string, "Sample heading")
        self.assertEqual(
            parsed_content_tabbed_indent[1][1].string, "> [!NOTE]\n> Non-indented block"
        )
        self.assertEqual(parsed_content_tabbed_indent[1][2].string, "Sample heading")
        self.assertEqual(parsed_content_tabbed_indent[1][3].string, " Sample sub-heading")
        self.assertEqual(
            parsed_content_tabbed_indent[1][4].string,
            " > [!NOTE]\n > This is an indented block"
        )

    def test_parse_indented_code_block_without_single_space(self):
        indent_content = u"""
Sample heading

>[!NOTE]
>Non-indented block

1. Sample heading

    Sample sub-heading

    >[!NOTE]
    >This is an indented block
"""
        expected_hashed_template = (
            "\n9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr"
            "\n\n3afcdbfeb6ecfbdd0ba628696e3cc163_tr\n\n"
            "1. 247730f9d0d2eaad265a470e32aa0cdf_tr\n\n"
            "   cdee9bf40a070d58d14dfa3bb61e0032_tr\n\n"
            "    7693e302dc09b57483d26522ef25feb4_tr\n"
        )
        parsed_content_indent = self.handler.parse(content=indent_content)

        self.assertEqual(parsed_content_indent[0], expected_hashed_template)
        self.assertEqual(len(parsed_content_indent[1]), 5)

        self.assertEqual(parsed_content_indent[1][0].string, "Sample heading")
        self.assertEqual(
            parsed_content_indent[1][1].string, ">[!NOTE]\n>Non-indented block"
        )
        self.assertEqual(parsed_content_indent[1][2].string, "Sample heading")
        self.assertEqual(parsed_content_indent[1][3].string, " Sample sub-heading")
        self.assertEqual(
            parsed_content_indent[1][4].string, 
            " >[!NOTE]\n >This is an indented block"
        )

    def test_find_fuzzy_substring(self):
        substring = "Here is a string"
        string = "Yes. Here    is a    string that we like"

        span = self.handler.find_fuzzy_substring(substring, string)
        assert span is not None
        assert span == (5, 27)

    def test_find_fuzzy_substring_no_match_when_extra_token_present(self):
        pattern = "Here is not a string"
        text = "Yes. Here    is a    string that we like"

        assert self.handler.find_fuzzy_substring(pattern, text) is None

    def test_empty_pattern_returns_none(self):
        assert self.handler.find_fuzzy_substring("", "anything at all") is None

class GithubMarkdownV2CustomTestCase(unittest.TestCase):
    """Tests some additional functionality of GithubMarkdownHandlerV2.

    More specifically, it tests various helper methods, to ensure
    full coverage and cover edge cases.
    """

    def setUp(self):
        self.handler = GithubMarkdownHandlerV2()

    def test_is_yaml_string_false_for_ints(self):
        openstring = OpenString('4', 'something')
        self.assertFalse(self.handler._is_yaml_string(openstring))

    def test_is_yaml_string_true_for_strings(self):
        openstring = OpenString('some.string.key', 'something')
        self.assertTrue(self.handler._is_yaml_string(openstring))

    def test_should_wrap_in_quotes_false_if_no_special_case(self):
        openstring = OpenString('k', u' Απλό case')
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertFalse(should_wrap)
        self.assertIsNone(wrap_char)

    def test_should_wrap_in_quotes_false_if_already_wrapped(self):
        openstring = OpenString('k', u'  "Κάτι άλλο "')
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertFalse(should_wrap)
        self.assertIsNone(wrap_char)

        openstring = OpenString('k', u"  'Κάτι άλλο' ")
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertFalse(should_wrap)
        self.assertIsNone(wrap_char)

    def test_should_wrap_in_quotes_if_starts_but_not_ends_with_quote(self):
        openstring = OpenString('k', u' " Κάτι άλλο ')
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertTrue(should_wrap)
        self.assertEqual(wrap_char, u"'")

        openstring = OpenString('k', u" ' Κάτι άλλο  ")
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertTrue(should_wrap)
        self.assertEqual(wrap_char, u'"')

    def test_should_wrap_in_quotes_if_starts_with_special_char(self):
        starting_chars = [
            GithubMarkdownHandlerV2.ASTERISK,
            GithubMarkdownHandlerV2.AMPERSAND,
            GithubMarkdownHandlerV2.DASH,
            GithubMarkdownHandlerV2.AT_SIGN,
        ]
        for char in starting_chars:
            openstring = OpenString('k', u' {} Κάτι άλλο '.format(char))
            should_wrap, wrap_char = self.handler._should_wrap_in_quotes(
                openstring
            )
            self.assertTrue(should_wrap)
            self.assertEqual(wrap_char, u'"')

    def test_should_wrap_in_quotes_if_has_special_char(self):
        special_chars = [
            GithubMarkdownHandlerV2.NEWLINE,
            GithubMarkdownHandlerV2.COLON,
            GithubMarkdownHandlerV2.HASHTAG,
        ]
        for char in special_chars:
            openstring = OpenString('k', u' Κάτι άλλο {} -'.format(char))
            should_wrap, wrap_char = self.handler._should_wrap_in_quotes(
                openstring
            )
            self.assertTrue(should_wrap)
            self.assertEqual(wrap_char, u'"')

    def test_should_wrap_in_quotes_if_starts_but_not_ends_with_bracket(self):
        openstring = OpenString('k', u' [Κάτι] άλλο ')
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(openstring)
        self.assertTrue(should_wrap)
        self.assertEqual(wrap_char, u'"')

    def test_should_not_wrap_in_quotes_if_has_pipe_char(self):
        openstring = OpenString('k', u'{} Something else'.format(GithubMarkdownHandlerV2.PIPE))
        should_wrap, wrap_char = self.handler._should_wrap_in_quotes(
            openstring
        )
        self.assertFalse(should_wrap)

    def test_wrap_in_quotes(self):
        """Make sure that the string is wrapped and that any existing quote chars
        are escaped."""
        wrapped = self.handler._wrap_in_quotes(u"To '21", "'")
        self.assertEqual(wrapped, u"'To ''21'")
        wrapped = self.handler._wrap_in_quotes(u'Αυτό είναι "ΟΚ"', '"')
        self.assertEqual(wrapped, u'"Αυτό είναι \\"ΟΚ\\""')

    def test_wrap_in_quotes_exception_for_wrong_quote(self):
        """Make sure that the a ValueError is raised if a wrong quote char is given."""
        self.assertRaises(ValueError, self.handler._wrap_in_quotes, u"To '21", "*")

    def test_transform_yaml_string_left_as_is(self):
        openstring = OpenString('k', u' Δεν θέλω τίποτα')
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, openstring.string)

    def test_transform_yaml_string_wrapped_for_brackets(self):
        openstring = OpenString('k', u' [Θέλω] quotes')
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, u'" [Θέλω] quotes"')

    def test_transform_yaml_string_wrapped__with_flag_single_quotes(self):
        openstring = OpenString('k', u' [Θέλω] quotes', flags=u"'")
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, u"' [Θέλω] quotes'")

    def test_transform_yaml_string_wrapped_with_flag_double_quotes(self):
        openstring = OpenString('k', u' [Θέλω] quotes', flags=u'"')
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, u'" [Θέλω] quotes"')

    def test_transform_yaml_string_wrapped_for_double_quotes(self):
        openstring = OpenString('k', u' "Θέλω" quotes')
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, u'\' "Θέλω" quotes\'')

    def test_transform_yaml_string_wrapped_for_at_sign(self):
        openstring = OpenString('k', u' @κάπου')
        string = self.handler._transform_yaml_string(openstring)
        self.assertEqual(string, u'" @κάπου"')

    def test_escape_control_characters(self):
        openstring = OpenString('k', u'者・最')  # 2nd character is the backspace char
        self.handler._escape_invalid_chars(openstring)
        self.assertEqual(openstring.string, u'者\\u0008・最')

        openstring = OpenString('k', {5: u'者・最', 1: u'AA', 2: u'aa'})
        self.handler._escape_invalid_chars(openstring)
        self.assertEqual(
            openstring.string, {5: u'者\\u0008・最', 1: u'\\u0008AA', 2: u'\\u0008aa'},
        )

    def test_unescape_control_characters_escapes_non_printable(self):
        openstring = OpenString(
            'k', u'start\\x01\\x02\\x03\\u0003\\x04\\u0004\\x05\\x06\\x07\\x08'
                 u'\\x10\\x11\\x12\\x1e\\x1F\\x7fend'
        )
        self.handler._unescape_non_printable(openstring)
        expected = u'start\x01\x02\x03\x03\x04\x04\x05\x06\x07\x08' \
                   u'\x10\x11\x12\x1e\x1F\x7fend'

        self.assertEqual(
            openstring.string,
            expected,
        )

    def test_unescape_control_characters_keeps_printable(self):
        openstring = OpenString(
            'k', u'start\x85\x00\x09\xA9\\u0041end'
        )
        self.handler._unescape_non_printable(openstring)
        self.assertEqual(openstring.string, u'start\x85\x00\x09\xA9\\u0041end')
