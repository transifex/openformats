import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import generate_random_string

from openformats.formats.json import JsonHandler


class JsonTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = JsonHandler
    TESTFILE_BASE = "openformats/tests/formats/json/files"

    def setUp(self):
        super(JsonTestCase, self).setUp()

        self.handler = JsonHandler()
        self.random_string = generate_random_string()
        self.random_openstring = OpenString("a", self.random_string)
        self.template_replacement = self.random_openstring.template_replacement

    def test_simple(self):
        # Using old-timey string formatting because of conflicts with '{'
        template, stringset = self.handler.parse('{"a": "%s"}' %
                                                 self.random_string)

        self.assertEquals(template, '{"a": "%s"}' % self.template_replacement)
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__,
                          self.random_openstring.__dict__)
