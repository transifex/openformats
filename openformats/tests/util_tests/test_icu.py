# -*- coding: utf-8 -*-

import unittest

from openformats.strings import OpenString
from openformats.utils.icu import (ICUCompiler, ICUParser, ICUString,
                                   normalize_plural_rule, PLURAL_FORMAT_NUMERIC,
                                   PLURAL_FORMAT_STRING)


class ICUStringTestCase(unittest.TestCase):
    """Test the ICUString class."""

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

    def test_syntax_by_rule(self):
        """Test the `syntax_by_rule` property."""
        icu_str = ICUString(
            'key',
            [
                ('=0', u'{0 pins}'),
                ('=1', u'{one pin}'),
                ('two', u'{a couple of pins}'),
                ('other', u'{{cnt} pins}')
            ],
            pluralized=True,
        )
        self.assertDictEqual(
            icu_str.syntax_by_rule,
            {
                0: PLURAL_FORMAT_NUMERIC,
                1: PLURAL_FORMAT_NUMERIC,
                2: PLURAL_FORMAT_STRING,
                5: PLURAL_FORMAT_STRING,
            },
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
    """Test the functionality of the ICUParser class.

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


class ICUCompilerSerializationTestCase(unittest.TestCase):
    """Test the serialization functionality of the ICUCompiler class."""

    def test_compile_with_default_delimiter(self):
        """Make sure that serialization with a default delimiter
        works as expected."""
        openstring = OpenString('key', {1: u'χαλί', 5: u'χαλιά'}, pluralized=True)
        string = ICUCompiler().serialize_strings(openstring.string)
        self.assertEqual(
            u'one {χαλί} other {χαλιά}',
            string,
        )

    def test_compile_with_custom_delimiter(self):
        """Make sure that serialization with a custom delimiter
        works as expected."""
        openstring = OpenString('key', {1: u'χαλί', 5: u'χαλιά'}, pluralized=True)
        string = ICUCompiler().serialize_strings(openstring.string, '\n')
        self.assertEqual(
            u'one {χαλί}\nother {χαλιά}',
            string,
        )

    def test_compile_with_custom_syntax_per_rule(self):
        """Make sure that serialization with a custom syntax
        works as expected."""
        openstring = OpenString(
            'key', {1: u'χαλί', 2: u'δύο χαλιά', 3: u'λίγα χαλιά', 5: u'χαλιά'},
            pluralized=True,
        )
        string = ICUCompiler().serialize_strings(
            openstring.string,
            syntax_by_rule={
                1: PLURAL_FORMAT_NUMERIC,
                2: PLURAL_FORMAT_NUMERIC,
                3: PLURAL_FORMAT_STRING,
                # omit the last one on purpose, should be rendered as string
            },
        )
        self.assertEqual(
            u'=1 {χαλί} =2 {δύο χαλιά} few {λίγα χαλιά} other {χαλιά}',
            string,
        )


class ICUCompilerPlaceholderCreationTestCase(unittest.TestCase):
    """Test the creation of placeholder hashes in the ICUCompiler
    class.

    Tests the _create_placeholders_by_rule() method.
    """

    def test_with_more_target_languages(self):
        icu_string = ICUParser().parse(
            'doesntmatter',
            u'{count, plural, one {ac76ac7a27_pl_0} other {ac76ac7a27_pl_1}}'
        )
        placeholders = ICUCompiler._create_placeholders_by_rule(
            icu_string,
            [1, 2, 3, 4, 5]
        )
        self.assertDictEqual(
            {
                1: u'ac76ac7a27_pl_0',
                2: u'ac76ac7a27_pl_1',
                3: u'ac76ac7a27_pl_2',
                4: u'ac76ac7a27_pl_3',
                5: u'ac76ac7a27_pl_4',
            },
            placeholders,
        )

    def test_with_less_target_languages(self):
        icu_string = ICUParser().parse(
            'doesntmatter',
            u'{count, plural, one {ac76ac7a27_pl_0} other {ac76ac7a27_pl_1}}'
        )
        placeholders = ICUCompiler._create_placeholders_by_rule(
            icu_string,
            [5]
        )
        self.assertDictEqual(
            {
                5: u'ac76ac7a27_pl_0',
            },
            placeholders,
        )


class ICUCompilerSerializePlaceholdersTestCase(unittest.TestCase):
    """Test the serialization of placeholder hashes in the ICUCompiler
    class.

    Tests the serialize_placeholder_string() method.
    """

    def test_with_more_target_plurals(self):
        icu_string = ICUParser().parse(
            'doesntmatter',
            u'{count, plural, one {ac76ac7a27_pl_0} other {ac76ac7a27_pl_1}}'
        )
        serialized = ICUCompiler().serialize_placeholder_string(
            icu_string,
            [1, 2, 3, 4, 5]
        )
        self.assertEqual(
            u'one {s}_0} two {s}_1} few {s}_2} many {s}_3} other {s}_4}'.replace(
                u'{s}', u'{ac76ac7a27_pl',
            ),
            serialized,
        )

    def test_with_less_target_plurals(self):
        icu_string = ICUParser().parse(
            'doesntmatter',
            u'{count, plural, one {ac76ac7a27_pl_0} few {ac76ac7a27_pl_1} '
            u'other {ac76ac7a27_pl_2}}'
        )
        serialized = ICUCompiler().serialize_placeholder_string(
            icu_string,
            [1, 5]
        )
        self.assertEqual(
            u'one {s}_0} other {s}_1}'.replace(
                u'{s}', u'{ac76ac7a27_pl',
            ),
            serialized,
        )

    def test_with_different_target_plurals(self):
        icu_string = ICUParser().parse(
            'doesntmatter',
            u'{count, plural, one {ac76ac7a27_pl_0} other {ac76ac7a27_pl_2}}'
        )
        serialized = ICUCompiler().serialize_placeholder_string(
            icu_string,
            [2, 5]
        )
        self.assertEqual(
            u'two {s}_0} other {s}_1}'.replace(
                u'{s}', u'{ac76ac7a27_pl',
            ),
            serialized,
        )
