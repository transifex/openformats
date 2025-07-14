import unittest
from io import open
from os import path

from openformats.formats.markdown_jsx import MarkdownJsxHandler
from openformats.tests.formats.common import CommonFormatTestMixin


class MarkdownJsxTestCase(CommonFormatTestMixin, unittest.TestCase):
    """Tests the basic functionality of MarkdownJsxHandler."""
    HANDLER_CLASS = MarkdownJsxHandler
    TESTFILE_BASE = "openformats/tests/formats/markdown_jsx/files"
    
    def __init__(self, *args, **kwargs):
        super(MarkdownJsxTestCase, self).__init__(*args, **kwargs)
        filepath = path.join(self.TESTFILE_BASE, "1_en.mdx")
        with open(filepath, "r", encoding='utf-8') as myfile:
            self.data['1_en'] = myfile.read()
            
    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en"])

    def test_parse(self):
        """Test parse converts tabs to spaces"""
        content_with_tab = self.handler.parse(content=u"# foo	bar")
        content_with_spaces = self.handler.parse(content=u"# foo    bar")
        self.assertEqual(content_with_tab[0], content_with_spaces[0])