import unittest

from openformats.formats.github_markdown import GithubMarkdownHandler
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils import translate_stringset


class GithubMarkdownTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = GithubMarkdownHandler
    TESTFILE_BASE = "openformats/tests/formats/github_markdown/files"

    def test_tabs_in_source_file(self):
        tmpl, strset = self.handler.parse(self.data["2_en"])
        translated_strset = translate_stringset(strset)
        translated_content = self.handler.compile(tmpl, translated_strset)
        self.assertEquals(translated_content, self.data["2_el"])
