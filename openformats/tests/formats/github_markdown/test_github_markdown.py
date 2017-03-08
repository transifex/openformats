import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.github_markdown import GithubMarkdownHandler


class GithubMarkdownTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = GithubMarkdownHandler
    TESTFILE_BASE = "openformats/tests/formats/github_markdown/files"
