import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.github_markdown import GithubMarkdownHandler


class GithubMarkdownTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = GithubMarkdownHandler
    TESTFILE_BASE = "openformats/tests/formats/github_markdown/files"

    def test_parse(self):
        """Test parse converts tabs to spaces"""

        content_with_tab = self.handler.parse(content=u"# foo	bar")
        content_with_spaces = self.handler.parse(content=u"# foo    bar")
        self.assertEqual(content_with_tab[0], content_with_spaces[0])
