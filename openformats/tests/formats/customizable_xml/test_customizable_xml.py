# -*- coding: utf-8 -*-
import unittest

import six

from openformats.exceptions import ParseError
from openformats.formats.customizable_xml import CustomizableXMLHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin

TEST_CONTENT = u"""
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <group name="group1">
    <str id="key1">
      <s>{s[0]}</s>
    </str>
    <str id="pressed_button">
      <s>{s[1]}</s>
      <alt info="male">{s[2]}</alt>
      <alt info="female">{s[3]}</alt>
    </str>
  </group>

  <group name="group2">
    <str id="key2">
      <s>{s[4]}</s>
    </str>
  </group>
</root>
"""

SOURCE_TRANSLATIONS = [
    u'A translatable string',
    u'The user pressed the button',
    u'He pressed the button',
    u'She pressed the button',
    u'Another translatable string',
]
GREEK_TRANSLATIONS = [
    u'Ένα κείμενο για μετάφραση',
    u'Ο χρήστης πάτησε το κουμπί',
    u'Αυτός πάτησε το κουμπί',
    u'Αυτή πάτησε το κουμπί',
    u'Ένα ακόμα κείμενο για μετάφραση',
]


class CustomizableXMLTestCase(CommonFormatTestMixin, unittest.TestCase):
    """Tests the functionality of the CustomizableXML handler."""

    HANDLER_CLASS = CustomizableXMLHandler
    TESTFILE_BASE = "openformats/tests/formats/customizable_xml/files"

    def test_customized_names(self):
        """Test custom options in XML structure, using default
        translations."""
        content = _get_test_content()
        handler = _get_custom_handler()
        template, stringset = handler.parse(content)

        compiled = handler.compile(template, _create_stringset())
        self.assertEqual(content, compiled)

    def test_customized_names_with_new_translations(self):
        """Test custom options in XML structure, using custom
        translations."""
        content = _get_test_content()
        handler = _get_custom_handler()
        template, stringset = handler.parse(content)

        new_translations = GREEK_TRANSLATIONS
        compiled = handler.compile(
            template, _create_stringset(new_translations),
        )
        self.assertEqual(_get_test_content(new_translations), compiled)

    def test_missing_root_node_on_parsing_raises_error(self):
        content = _get_test_content()
        handler = CustomizableXMLHandler(
            root_name='invalid',  # anything other than 'root'
        )
        with self.assertRaises(ParseError) as context:
            handler.parse(content)
        self.assertEqual(
            six.text_type(context.exception),
            u'Root node "<invalid>" not found',
        )

    def test_missing_key_in_string_node_on_parsing_raises_error(self):
        content = _get_test_content()
        handler = _get_custom_handler()
        handler.string_key_name = 'mykey'  # anything other than 'key'

        with self.assertRaises(ParseError) as context:
            handler.parse(content)
        self.assertEqual(
            six.text_type(context.exception),
            u'Missing "{key}" attribute in <{string}> node, '
            u'parent of "<{tag}>A translatable string</{tag}>"'.format(
                key=handler.string_key_name,
                string=handler.string_name,
                tag='s',
            )
        )

    def test_missing_root_node_on_compiling_raises_error(self):
        content = _get_test_content()
        handler = _get_custom_handler()
        template, stringset = handler.parse(content)

        handler.root_name = 'invalid'  # anything other than 'root'
        with self.assertRaises(ParseError) as context:
            handler.compile(template, _create_stringset())
        self.assertEqual(
            six.text_type(context.exception),
            u'Root node "<invalid>" not found',
        )


def _create_stringset(translations=None):
    """Get a list of OpenString objects to use in compilation.

    :param list translations: the list of str objects to use as translations,
        or the default source translations, if omitted
    :return: a list of OpenString objects
    :rtype: list
    """
    translations = translations or SOURCE_TRANSLATIONS
    return [
        OpenString('key', string, order=index)
        for index, string in enumerate(translations)
    ]


def _get_test_content(translations=None):
    """Get a content as an XML string, containing the given translations.

    If no translations are provided, the default source translations
    are used.

    :param list translations: a list of str objects to use,
        or the default source translations if omitted
    :return: the XML string
    :rtype: str
    """
    translations = translations or SOURCE_TRANSLATIONS
    return TEST_CONTENT.format(s=translations)


def _get_custom_handler():
    """Get a new handler that uses specific custom options
    that are compatible with the structure of TEST_CONTENT.

    :return: a new handler instance
    :rtype: CustomizableXMLHandler
    """
    return CustomizableXMLHandler(
        root_name='root',
        section_name='group',
        section_id_name='name',
        string_name='str',
        string_key_name='id',
        base_string_name='s',
        variant_string_name='alt',
        variant_string_id_name='info',
    )
