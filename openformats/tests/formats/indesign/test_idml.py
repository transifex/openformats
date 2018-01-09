import unittest

from openformats.formats.indesign import InDesignHandler


class InDesignTestCase(unittest.TestCase):
    HANDLER_CLASS = InDesignHandler
    TESTFILE_BASE = "openformats/tests/formats/indesign/files"

    def test_parse_and_compile(self):
        """Test parsing to template and re-compiling to the initial file."""

        _file = open("%s/sample.idml" % self.TESTFILE_BASE, "r")
        _file_enc = _file.read()

        handler = self.HANDLER_CLASS()

        template, stringset = handler.parse(_file_enc)
        finalidml = handler.compile(template, stringset)

        template2, stringset2 = self.HANDLER_CLASS().parse(finalidml)

        self.assertEqual(str(stringset), str(stringset2))
        self.assertEqual(template, template2)

    def test_parser(self):
        """Test parsing to template and re-compiling to the initial file."""

        _file = open("%s/sample.idml" % self.TESTFILE_BASE, "r")
        _file_enc = _file.read()

        handler = self.HANDLER_CLASS()

        template, stringset = handler.parse(_file_enc)
        template2, stringset2 = self.HANDLER_CLASS().parse(template)

        for string in stringset2:
            self.assertEqual(string.string[-3:], "_tr")
