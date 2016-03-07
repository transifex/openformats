import unittest

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.android import AndroidHandler


class AndroidTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidHandler
    TESTFILE_BASE = "openformats/tests/formats/android/files"
