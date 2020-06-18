import unittest
from io import open
from os import path

import six

from openformats.formats.yaml import I18nYamlHandler
from openformats.tests.formats.common import CommonFormatTestMixin


class I18nYamlTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = I18nYamlHandler
    TESTFILE_BASE = "openformats/tests/formats/" \
                    "yamlinternationalization/files"

    def setUp(self):
        self.handler = self.HANDLER_CLASS()
        self.handler.set_plural_rules([1, 5])
        self.handler.set_lang_code('en')
        self.read_files()
        self.tmpl, self.strset = self.handler.parse(self.data["1_en"])

    def __init__(self, *args, **kwargs):
        super(I18nYamlTestCase, self).__init__(*args, **kwargs)
        extra_files = ["1_en_exported.yml",
                       "1_en_exported_no_translations.yml"]

        for fname in extra_files:
            filepath = path.join(self.TESTFILE_BASE, fname)
            with open(filepath, "r", encoding='utf-8') as myfile:
                self.data[fname[:-4]] = myfile.read()

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content, self.data["1_en_exported"])

    def test_compile_with_missing_translations(self):
        # The entries with these keys should be included in the compiled
        # result, the rest should be completely absent
        keys_to_keep = [
            'pluralized_string_with_extra_keys',
            'title', 'intro', 'key1.[0].list_key.[1]',
            'key2.[0].object_within_list', 'custom_vars.var2',
            'value with start backtick', 'emojis', 'anchor_with_label.anchor_test',
            'anchor_with_label.testing_alias.[2]',
        ]
        for openstring in self.strset:
            for rule, pluralform in list(six.iteritems(openstring._strings)):
                if openstring.key in keys_to_keep:
                    openstring._strings[rule] = u"{}:{}".format(
                        'el', pluralform
                    )
                else:
                    openstring._strings[rule] = u""

        self.handler.should_remove_empty = True
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEqual(remade_orig_content,
                         self.data["1_en_exported_no_translations"])
