import unittest

from openformats.tests.formats.common import CommonFormatTestMixin

from openformats.formats.android import JsonPluralsHandler


class JsonPluralsTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = JsonPluralsHandler
    TESTFILE_BASE = "openformats/tests/formats/keyvaluejson_plurals/files"
