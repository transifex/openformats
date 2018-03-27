import unittest
from os import path

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.yaml import YamlHandler


class YamlTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = YamlHandler
    TESTFILE_BASE = "openformats/tests/formats/yaml/files"

    def __init__(self, *args, **kwargs):
        super(YamlTestCase, self).__init__(*args, **kwargs)
        filepath = path.join(self.TESTFILE_BASE, "1_en_exported.yml")
        with open(filepath, "r") as myfile:
            self.data['1_en_exported'] = myfile.read().decode("utf-8")

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEquals(remade_orig_content, self.data["1_en_exported"])
