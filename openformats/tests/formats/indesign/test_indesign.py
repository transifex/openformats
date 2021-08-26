# -*- coding: utf-8 -*-
import unittest
from io import open

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

        self.assertEqual([hash(string) for string in stringset],
                         [hash(string) for string in stringset2])
        self.assertEqual(template, template2)

    def test_extracts_raw(self):
        if self.HANDLER_CLASS.EXTRACTS_RAW:
            self.assertTrue(hasattr(self.HANDLER_CLASS, 'escape'))
            self.assertTrue(hasattr(self.HANDLER_CLASS, 'unescape'))

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
            u'A simple string',
            u'A simple string with special <?ACE 7?> character',
            u'Ενα απλό string',
            u'<?ACE 8?> string <Br/>;',
            u'\ufeff  #',
            u'\ufef0  ()',
            u'\ufef0  A',
        ]
        invalid_strings = [
            u' ',
            u'   <?ACE 7?> ',
            u'',
            u'<?ACE 8?> <Br/>;',
            u'\ufeff',
            u' \ufeff ',
            u' \ufeff 5',
            u'\ufeff<Br/>;',
        ]

        for string in valid_strings:
            self.assertFalse(handler._can_skip_content(string))

        for string in invalid_strings:
            self.assertTrue(handler._can_skip_content(string))

    def test_find_and_replace_simple_story(self):
        handler = self.HANDLER_CLASS()
        simple_input = u"""
            <Story>
              <Content>One string</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """

        simple_output = u"""
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
        simple_story_template = u"""
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        simple_compiled_story = u"""
            <Story>
              <Content>Some string 1</Content>
              <Content>Some string 2</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        handler = self.HANDLER_CLASS()
        handler.stringset = [
            OpenString(u"0", u"Some string 1", order=0),
            OpenString(u"1", u"Some string 2", order=1),
        ]

        compiled_story = handler._compile_story(simple_story_template)
        self.assertEqual(compiled_story, simple_compiled_story)

    def test_compile_story_missing_strings(self):
        simple_story_template = u"""
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        simple_compiled_story = u"""
            <Story>
              <Content>Some string 1</Content>
              <Content></Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        handler = self.HANDLER_CLASS()
        handler.stringset = [
            OpenString(u"0", u"Some string 1", order=0),
        ]

        compiled_story = handler._compile_story(simple_story_template)
        self.assertEqual(compiled_story, simple_compiled_story)

    def test_compile_two_stories_with_strings(self):
        first_story_template = u"""
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>3afcdbfeb6ecfbdd0ba628696e3cc163_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        second_story_template = u"""
            <Story>
              <Content>9a1c7ee2c7ce38d4bbbaf29ab9f2ac1e_tr</Content>
              <Content>cdee9bf40a070d58d14dfa3bb61e0032_tr</Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        expected_first_compiled_story = u"""
            <Story>
              <Content>Some string 1</Content>
              <Content></Content>
              <Metadata></Metadata>
              <Content>  <?ACE 7?></Content>
            </Story>
        """
        expected_second_compiled_story = u"""
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
            OpenString(u"0", u"Some string 1", order=0),
            OpenString(u"3", u"Some string 2", order=3),
        ]

        first_compiled_story = handler._compile_story(
            first_story_template
        )
        second_compiled_story = handler._compile_story(
            second_story_template
        )
        self.assertEqual(first_compiled_story, expected_first_compiled_story)
        self.assertEqual(second_compiled_story, expected_second_compiled_story)

    def test_compile_story_with_amps(self):
        regular = OpenString('0', u"hello world", order=0)
        with_amp = OpenString('1', u"hello &world", order=1)
        with_amp_escaped = OpenString('2', u"hello &lt;world", order=2)
        many_amps = OpenString('3', u"&&#x0a1f;&&", order=3)

        base_template = u"""
            <Story>
                <Content>{regular}</Content>
                <Content>{with_amp}</Content>
                <Content>{with_amp_escaped}</Content>
                <Content>{many_amps}</Content>
            </Story>
        """

        template = base_template.format(
            regular=regular.template_replacement,
            with_amp=with_amp.template_replacement,
            with_amp_escaped=with_amp_escaped.template_replacement,
            many_amps=many_amps.template_replacement,
        )
        expected_compiled_story = base_template.format(
            regular=u"hello world",
            with_amp=u"hello &amp;world",
            with_amp_escaped=u"hello &lt;world",
            many_amps=u"&amp;&#x0a1f;&amp;&amp;",
        )

        handler = self.HANDLER_CLASS()
        handler.stringset = [regular, with_amp, with_amp_escaped, many_amps]
        compiled_story = handler._compile_story(template)
        self.assertEqual(compiled_story, expected_compiled_story)

    def test_compile_story_with_lts(self):
        regular = OpenString('0', u"hello world", order=0)
        with_lt = OpenString('1', u"hello <world", order=1)
        with_lt_escaped = OpenString('2', u"hello &lt;world", order=2)
        with_mixed_lts = OpenString('3', u"hello &lt;<world", order=3)

        base_template = u"""
            <Story>
                <Content>{regular}</Content>
                <Content>{with_lt}</Content>
                <Content>{with_lt_escaped}</Content>
                <Content>{with_mixed_lts}</Content>
            </Story>
        """

        template = base_template.format(
            regular=regular.template_replacement,
            with_lt=with_lt.template_replacement,
            with_lt_escaped=with_lt_escaped.template_replacement,
            with_mixed_lts=with_mixed_lts.template_replacement,
        )
        expected_compiled_story = base_template.format(
            regular=u"hello world",
            with_lt=u"hello &lt;world",
            with_lt_escaped=u"hello &lt;world",
            with_mixed_lts=u"hello &lt;&lt;world",
        )

        handler = self.HANDLER_CLASS()
        handler.stringset = [regular, with_lt, with_lt_escaped, with_mixed_lts]
        compiled_story = handler._compile_story(template)
        self.assertEqual(compiled_story, expected_compiled_story)
