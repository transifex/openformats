import unittest

from openformats.formats.indesign import InDesignHandler


class InDesignTestCase(unittest.TestCase):
    HANDLER_CLASS = InDesignHandler
    TESTFILE_BASE = "openformats/tests/formats/indesign/files"

    def test_special_symbols_parsing(self):
        """Test if the spcial IDML symbols are correctly preserved."""

        _file = open("%s/sample.xml" % self.TESTFILE_BASE, "r")
        xml = _file.read()

        handler = self.HANDLER_CLASS()

        parsed = handler._preserve_symbols(xml)

        self.assertIn("&amp;#x200F;", parsed)
        self.assertIn("&amp;#x200B;", parsed)

        compiled = handler._restore_symbols(parsed)

        self.assertIn("&#x200B;", compiled)
        self.assertEqual(compiled, xml)
