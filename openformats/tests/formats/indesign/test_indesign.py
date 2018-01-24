# -*- coding: utf-8 -*-
import unittest

from openformats.formats.indesign import InDesignHandler
from openformats.strings import OpenString


class InDesignTestCase(unittest.TestCase):
    HANDLER_CLASS = InDesignHandler
    TESTFILE_BASE = "openformats/tests/formats/indesign/files"

    def test_parse_and_compile(self):
        """Test parsing to template and re-compiling to the initial file."""

        with open("%s/sample.idml" % self.TESTFILE_BASE, "rb") as _file:
            _file_enc = _file.read()

        handler = self.HANDLER_CLASS()

        template, stringset = handler.parse(_file_enc)
        finalidml = handler.compile(template, stringset)

        template2, stringset2 = self.HANDLER_CLASS().parse(finalidml)

        self.assertEqual(str(stringset), str(stringset2))
        self.assertEqual(template, template2)

    def test_parser(self):
        """Test parsing to template and validate template."""

        with open("%s/sample.idml" % self.TESTFILE_BASE, "rb") as _file:
            _file_enc = _file.read()

        handler = self.HANDLER_CLASS()

        template, stringset = handler.parse(_file_enc)
        template2, stringset2 = self.HANDLER_CLASS().parse(template)

        self.assertEqual(len(stringset), len(stringset2))
        for string in stringset2:
            self.assertEqual(string.string[-3:], "_tr")

    def test_can_skip_content(self):
        """ Test cases when a string sould be skipped """
        handler = self.HANDLER_CLASS()
        valid_strings = [
            'A simple string',
            'A simple string with special <?ACE 7?> character',
            'Ενα απλό string',
            '<?ACE 8?> string <Br/>;',
        ]
        invalid_strings = [
            ' ',
            '   <?ACE 7?> ',
            '',
            '<?ACE 8?> <Br/>;',
        ]

        for string in valid_strings:
            self.assertFalse(handler._can_skip_content(string))

        for string in invalid_strings:
            self.assertTrue(handler._can_skip_content(string))

    def test_find_and_replace_simple_story(self):
        handler = self.HANDLER_CLASS()
        simple_input = """
            <Story>
              <Content>One string</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """

        simple_output = """
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        out = handler._find_and_replace(simple_input)
        self.assertEqual(out, simple_output)
        self.assertEqual(len(handler.stringset), 1)

    def test_compile_story(self):
        simple_story_template = """
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        simple_compiled_story = """
            <Story>
              <Content>Some string 1</Content>
              <Content>Some string 2</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        handler = self.HANDLER_CLASS()
        handler.stringset = [
            OpenString(str(0), "Some string 1", order=0),
            OpenString(str(1), "Some string 2", order=1),
        ]

        compiled_story = handler._compile_story(simple_story_template)
        self.assertEqual(compiled_story, simple_compiled_story)

    def test_compile_story_missing_strings(self):
        simple_story_template = """
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        simple_compiled_story = """
            <Story>
              <Content>Some string 1</Content>
              <Content></Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        handler = self.HANDLER_CLASS()
        handler.stringset = [
            OpenString(str(0), "Some string 1", order=0),
        ]

        compiled_story = handler._compile_story(simple_story_template)
        self.assertEqual(compiled_story, simple_compiled_story)

    def test_compile_two_stories_with_strings(self):
        first_story_template = """
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        second_story_template = """
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>cdee9bf40a070d58d14dfa3bb61e0032_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        expected_first_compiled_story = """
            <Story>
              <Content>Some string 1</Content>
              <Content></Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        expected_second_compiled_story = """
            <Story>
              <Content></Content>
              <Content>Some string 2</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        # strings #1 and #2 are missing from the stringset
        handler = self.HANDLER_CLASS()
        handler.stringset = [
            OpenString(str(0), "Some string 1", order=0),
            OpenString(str(3), "Some string 2", order=3),
        ]

        first_compiled_story = handler._compile_story(
            first_story_template
        )
        second_compiled_story = handler._compile_story(
            second_story_template
        )
        self.assertEqual(first_compiled_story, expected_first_compiled_story)
        self.assertEqual(second_compiled_story, expected_second_compiled_story)
