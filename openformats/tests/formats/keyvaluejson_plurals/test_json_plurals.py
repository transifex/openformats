import unittest

from openformats.strings import OpenString

from openformats.formats.json_plurals import JsonPluralsHandler
from ..beta_keyvaluejson.test_json import JsonTestCase
from openformats.tests.utils.strings import generate_random_string


class JsonPluralsTestCase(JsonTestCase):

    HANDLER_CLASS = JsonPluralsHandler
    TESTFILE_BASE = "openformats/tests/formats/keyvaluejson_plurals/files"

    def setUp(self):
        super(JsonPluralsTestCase, self).setUp()
        self.handler = JsonPluralsHandler()
