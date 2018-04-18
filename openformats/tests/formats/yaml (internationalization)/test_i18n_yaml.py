import unittest
from os import path

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.formats.yaml import I18nYamlHandler


class I18nYamlTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = I18nYamlHandler
    TESTFILE_BASE = "openformats/tests/formats/" \
                    "yaml (internationalization)/files"

    def setUp(self):
        self.handler = self.HANDLER_CLASS()
        self.handler.set_plural_rules([1, 5])
        self.handler.set_lang_code('en')
        self.read_files()
        self.tmpl, self.strset = self.handler.parse(self.data["1_en"])

    def __init__(self, *args, **kwargs):
        super(I18nYamlTestCase, self).__init__(*args, **kwargs)
        extra_files = ["1_en_exported.yml",
                       "1_en_exported_without_template.yml"]

        for fname in extra_files:
            filepath = path.join(self.TESTFILE_BASE, fname)
            with open(filepath, "r") as myfile:
                self.data[fname[:-4]] = myfile.read().decode("utf-8")

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEquals(remade_orig_content, self.data["1_en_exported"])

    def test_compile_without_template(self):
        """Test that import-export is the same as the original file."""
        self.handler.should_use_template = False
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEquals(remade_orig_content,
                          self.data["1_en_exported_without_template"])
