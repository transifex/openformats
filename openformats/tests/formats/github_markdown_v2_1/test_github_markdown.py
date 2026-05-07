# -*- coding: utf-8 -*-
import unittest
from io import open
from os import path

from openformats.formats.github_markdown_v2_1 import GithubMarkdownHandlerV2_1
from openformats.tests.formats.common import CommonFormatTestMixin

unittest.TestCase.maxDiff = None


class GithubMarkdownV2_1TestCase(CommonFormatTestMixin, unittest.TestCase):
    """Tests the basic functionality of GithubMarkdownHandlerV2_1.

    V2_1 inherits V2 and only differs in the block grammar: fences with a
    CommonMark info string (e.g. ```js lines) are accepted instead of falling
    back to a paragraph that swallows following headings. The fixtures are
    identical to V2's because no fixture trips the fence bug, so the
    expected parse/compile output is byte-identical to V2.
    """
    HANDLER_CLASS = GithubMarkdownHandlerV2_1
    TESTFILE_BASE = "openformats/tests/formats/github_markdown_v2_1/files"

    def __init__(self, *args, **kwargs):
        super(GithubMarkdownV2_1TestCase, self).__init__(*args, **kwargs)
        filepath = path.join(self.TESTFILE_BASE, "1_en_export.md")
        with open(filepath, "r", encoding='utf-8') as myfile:
            self.data['1_en_export'] = myfile.read()

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en_export"])

    def test_parse(self):
        """Test parse converts tabs to spaces"""
        content_with_tab = self.handler.parse(content=u"# foo\tbar")
        content_with_spaces = self.handler.parse(content=u"# foo    bar")
        self.assertEqual(content_with_tab[0], content_with_spaces[0])

    def test_fence_with_info_string_keeps_block_intact(self):
        # CommonMark allows free-form info strings after the language id
        # (e.g. ```js lines). Mistune 0.8 only accepts a single \S+ token,
        # so without our grammar override the fence rule fails on the
        # opening line, the entire block is mis-parsed as a paragraph, and
        # the paragraph rule keeps consuming through any following heading
        # (because the closing ``` alone is not a fence either). The
        # fixture mirrors the customer's real MDX: no blank lines between
        # the prose, the fenced block and the next heading. See TX-17120.
        source = (
            u"Copy the following code to the Actions Code Editor:\n"
            u"```js lines\n"
            u"exports.onExecutePostLogin = async (event, api) => {\n"
            u'  api.access.deny("end_users_not_allowed");\n'
            u"}\n"
            u"```\n"
            u"If a user attempts to access during the weekend, "
            u"access will be denied.\n"
            u"## Allow access only to corporate users\n"
            u"Body paragraph after the heading.\n"
        )
        _, stringset = self.handler.parse(source)
        strings = [s.string for s in stringset]

        # Heading must be its own entry, with the leading ## stripped.
        self.assertIn(u"Allow access only to corporate users", strings)
        self.assertIn(u"Body paragraph after the heading.", strings)

        # The heading must not be swallowed by another stringset entry.
        leaked = [
            s for s in strings
            if u"Allow access only to corporate users" in s
            and s != u"Allow access only to corporate users"
        ]
        self.assertEqual(
            leaked, [],
            "heading text leaked into another stringset entry: %r" % leaked,
        )
