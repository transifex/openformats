import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.github_markdown_v2 import GithubMarkdownHandlerV2


unittest.TestCase.maxDiff = None


class GithubMarkdownTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = GithubMarkdownHandlerV2
    TESTFILE_BASE = "openformats/tests/formats/github_markdown_v2/files"
