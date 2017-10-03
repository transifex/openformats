import unittest

from os import path

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.github_markdown_v2 import GithubMarkdownHandlerV2


unittest.TestCase.maxDiff = None


class GithubMarkdownV2TestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = GithubMarkdownHandlerV2
    TESTFILE_BASE = "openformats/tests/formats/github_markdown_v2/files"

    def __init__(self, *args, **kwargs):
        super(GithubMarkdownV2TestCase, self).__init__(*args, **kwargs)
        filepath = path.join(self.TESTFILE_BASE, "1_en_export.md")
        with open(filepath, "r") as myfile:
            self.data['1_en_export'] = myfile.read().decode("utf-8")

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEquals(remade_orig_content, self.data["1_en_export"])

    def test_parse(self):
        """Test parse converts tabs to spaces"""
        content_with_tab = self.handler.parse(content=u"# foo	bar")
        content_with_spaces = self.handler.parse(content=u"# foo    bar")
        self.assertEqual(content_with_tab[0], content_with_spaces[0])
