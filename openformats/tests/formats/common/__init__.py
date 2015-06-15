import fnmatch
import re

from os import listdir, path
from os.path import isfile, join

from openformats.exceptions import ParseError
from openformats.tests.utils import translate_stringset


class CommonFormatTestMixin(object):
    """
    Define a set of tests to be run by every file format.

    The class that inherits from this must define the following:

    * ``HANDLER_CLASS``, eg: PlaintextHandler
    * ``TESTFILE_BASE``, eg: `openformats/tests/formats/plaintext/files`
    """

    TESTFILE_BASE = None
    HANDLER_CLASS = None

    def __init__(self, *args, **kwargs):
        self.data = {}
        super(CommonFormatTestMixin, self).__init__(*args, **kwargs)

    def read_files(self, ftypes=('en', 'el', 'tpl')):
        """
        Read test data files into variables.

        Example: 1_en.txt stored into self.data["1_en"]
        """

        # Find source files to use as a base to read all others
        en_files = []
        for f in listdir(self.TESTFILE_BASE):
            if (isfile(join(self.TESTFILE_BASE, f)) and
                    fnmatch.fnmatch(f, '[!.]*_en.*')):
                en_files.append(f)

        file_nums = set([f.split("_")[0] for f in en_files])
        for num in file_nums:
            for ftype in ftypes:
                name = "%s_%s" % (num, ftype)  # 1_en, 1_fr etc.
                filepath = path.join(self.TESTFILE_BASE, "%s.%s" % (
                    name, self.HANDLER_CLASS.extension))
                if not isfile(filepath):
                    self.fail("Bad test files: Expected to find %s" % filepath)
                with open(filepath, "r") as myfile:
                    self.data[name] = myfile.read().decode("utf-8")

    def setUp(self):
        self.handler = self.HANDLER_CLASS()
        self.read_files()
        self.tmpl, self.strset = self.handler.parse(self.data["1_en"])
        super(CommonFormatTestMixin, self).setUp()

    def test_template(self):
        """Test that the template created is the same as static one."""
        # FIXME: Test descriptions should have the handler's name prefixed to
        # be able to differentiate between them.
        self.assertEquals(self.tmpl, self.data["1_tpl"])

    def test_no_empty_strings_in_handler_stringset(self):
        for s in self.strset:
            self.assertFalse(s.string == '')

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        remade_orig_content = self.handler.compile(self.tmpl, self.strset)
        self.assertEquals(remade_orig_content, self.data["1_en"])

    def test_translate(self):
        """Test that translate + export is the same as the precompiled file."""
        translated_strset = translate_stringset(self.strset)
        translated_content = self.handler.compile(self.tmpl, translated_strset)
        self.assertEquals(translated_content, self.data["1_el"])

    def _test_parse_error(self, source, error_msg):
        """
        Test that trying to parse 'source' raises an error with a message
        exactly like 'error_msg'
        """
        self.assertRaisesRegexp(ParseError,
                                r'^{}$'.format(re.escape(error_msg)),
                                lambda: self.handler.parse(source))
