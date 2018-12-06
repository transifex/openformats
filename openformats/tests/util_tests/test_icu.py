# -*- coding: utf-8 -*-

import unittest

from openformats.strings import OpenString
from openformats.utils.icu import (ICUCompiler, ICUParser, ICUString,
                                   normalize_plural_rule)


class ICUStringTestCase(unittest.TestCase):

    def test_strings_by_rule(self):
        """Make sure the strings_by_rule property works properly."""
        icu_str = ICUString(
            'key',
            [
                ('zero', u'{0 lamparas}'),
                ('one', u'{1 lámpara}'),
                ('other', u'{{cnt} lamparas}')
            ],
            pluralized=True,
        )
        self.assertDictEqual(
            icu_str.strings_by_rule,
            {0: u'0 lamparas', 1: u'1 lámpara', 5: u'{cnt} lamparas'},
        )

    def test_icustring_representation(self):
        """This test is for coverage."""
        icu_str = ICUString(
            'key',
            [
                ('zero', u'0 lamparas'),
                ('one', u'1 lámpara'),
                ('other', u'{cnt} lamparas')
            ],
            pluralized=True,
        )
        icu_str.string_to_replace = 'doesntmatter'
        icu_str.current_position = 5  # any number, doesn't matter

        format_str = u'ICUString key={}, string_to_replace={}, pluralized={}, ' \
            'string_info={}, current_position={}'
        self.assertEqual(
            repr(icu_str),
            format_str.format(
                'key',
                icu_str.string_to_replace,
                icu_str.pluralized,
                repr(icu_str.string_info),
                icu_str.current_position,
            ),
        )


class ICUParserTestCase(unittest.TestCase):
    """Test the functionality of the ICU module.

    Most of its functionality is covered in the JSON tests, so here
    we only cover a few parts, namely:
     - the parsing of the `=N` syntax (including the conversion of numeric rules
       to string rules
     - minor things like the string representation of the ICUString class
    """

    def test_numeric_syntax_parsed_successfully(self):
        """If allow_numeric_plural_values=True, strings with =N syntax
        should not be parsed as pluralized."""
        parser = ICUParser(allow_numeric_plural_values=True)
        icu_str = parser.parse('key', u'{count, plural, =1 {μπάλα} other {μπάλες}}')
        self.assertDictEqual(
            icu_str.strings_by_rule,
            {1: u'μπάλα', 5: u'μπάλες'}
        )

        # Test default constructor - should support =N syntax
        parser = ICUParser()
        icu_str = parser.parse('key', u'{count, plural, =1 {μπάλα} other {μπάλες}}')
        self.assertDictEqual(
            icu_str.strings_by_rule,
            {1: u'μπάλα', 5: u'μπάλες'}
        )

    def test_numeric_syntax_ignored(self):
        """If allow_numeric_plural_values=False, strings with =N syntax
        should not be parsed as pluralized."""
        parser = ICUParser(allow_numeric_plural_values=False)
        icu_str = parser.parse('key', u'{count, plural, =1 {μπάλα} other {μπάλες}}')
        self.assertIsNone(icu_str)

    def test_plural_rule_normalization(self):
        """The the conversions made by the normalize_plural_rule() function."""
        self.assertEqual(normalize_plural_rule('=0'), 'zero')
        self.assertEqual(normalize_plural_rule('=1'), 'one')
        self.assertEqual(normalize_plural_rule('=2'), 'two')
        self.assertEqual(normalize_plural_rule('anything'), 'anything')


class ICUCompilerTestCase(unittest.TestCase):
    """Test the functionality of the ICU module."""
    def test_compiler(self):
        """Make sure that ICUCompiler works as expected."""
        openstring = OpenString('key', {1: u'χαλί', 5: u'χαλιά'}, pluralized=True)
        string = ICUCompiler().serialize_string(openstring)
        self.assertEqual(
            u'one {χαλί} other {χαλιά}',
            string,
        )
