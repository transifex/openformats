from __future__ import absolute_import

import itertools

from openformats.exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.xml import NewDumbXml
from ..utils.xmlutils import reraise_syntax_as_parse_errors


# These are the default values of the tags and attributes
# that will be used for parsing and compiling, if no custom
# values are provided
DEFAULT_ROOT_NAME = 'strings'
DEFAULT_SECTION_NAME = 'section'
DEFAULT_SECTION_ID_NAME = 'name'
DEFAULT_STRING_NAME = 'string'
DEFAULT_STRING_KEY_NAME = 'key'
DEFAULT_BASE_STRING_NAME = 'base'
DEFAULT_VARIANT_STRING_NAME = 'variant'
DEFAULT_VARIANT_STRING_CONTEXT_NAME = 'context'

# NOTE: Additional customization that can be implemented in the future:
# - keys include the section name as well
# - translatable text can be either in a tag like <base> or
#   as the text of the <string> tag
# - sections support nesting

# When a string key is composed of various parts,
# they are joined together using this delimiter, e.g.
# <string key="some_key>
#   <base>...</base>
#   <variant context="some_context">...</variant>
# </string>
# -> the string key of the variant string will be: "some_key::some_context"
COMPOSITE_KEY_SEPARATOR = '::'


class CustomizableXMLHandler(Handler):
    """A file format that supports XML files whose structure
    is customizable to a certain degree.

    The structure looks like this:
    <strings>
      <section name="group1">
        <string key="key1">
          <base>A translatable string</base>
        </string>
        <string key="pressed_button">
          <base>The user pressed the button</base>
          <variant context="male">He pressed the button</variant>
          <variant context="female">She pressed the button</variant>
        </string>
      </section>

      <section name="group2">
        <string key="key2">
          <base>Another translatable string</base>
        </string>
      </section>
    </strings>

    The structure must be followed as shown above, but the names of
    all tags and attributes can be customized. For example, the following
    is also supported:
    <root>
      <group name="group1">
        <str id="key1">
          <base>A translatable string</base>
        </str>
        <str id="pressed_button">
          <base>The user pressed the button</base>
          <alt context="male">He pressed the button</alt>
          <alt context="female">She pressed the button</alt>
        </str>
      </group>
    </root>
    """

    name = "CUSTOM_XML"
    extension = "xml"
    EXTRACTS_RAW = False

    def __init__(self, **kwargs):
        super(CustomizableXMLHandler, self).__init__()
        # Setup the customization
        # Use the provided values or fallback to the defaults
        self.root_name = kwargs.get('root_name', DEFAULT_ROOT_NAME)
        self.section_name = kwargs.get('section_name', DEFAULT_SECTION_NAME)
        self.section_id_name = kwargs.get(
            'section_id_name', DEFAULT_SECTION_ID_NAME
        )
        self.string_name = kwargs.get('string_name', DEFAULT_STRING_NAME)
        self.string_key_name = kwargs.get(
            'string_key_name', DEFAULT_STRING_KEY_NAME
        )
        self.base_string_name = kwargs.get(
            'base_string_name', DEFAULT_BASE_STRING_NAME
        )
        self.variant_string_name = kwargs.get(
            'variant_string_name', DEFAULT_VARIANT_STRING_NAME
        )
        self.variant_string_context_name = kwargs.get(
            'variant_string_id_name', DEFAULT_VARIANT_STRING_CONTEXT_NAME
        )

        # Define some variables
        self.transcriber = None
        self.stringset = None
        self.next_string = None

    @reraise_syntax_as_parse_errors
    def parse(self, content, **kwargs):
        """Parse the given string content and return a template and
        a stringset of the parsed content.

        The template will contain placeholders in the place of all
        translatable strings.

        :param str content: the complete string to parse
        :return: the template and the parsed stringset
        :rtype: tuple(str, list(OpenString))
        :raise ParseError: if any of required nodes or attributes
            are not found in `content`
        """
        order_counter = itertools.count()
        transcriber = Transcriber(content)
        source = transcriber.source

        # Everything starts at the root tag
        root_tag_pos = self._get_root_node_pos(content)
        parsed = NewDumbXml(source, root_tag_pos)
        stringset = []

        # Translatable content is organized under <section> tags
        for section_tag in parsed.find_children(self.section_name):

            # Find all <string> children tags
            for string_tag in section_tag.find_children(self.string_name):
                base_strings = list(string_tag.find_children(self.base_string_name))
                variants = list(string_tag.find_children(self.variant_string_name))
                all_tags = sorted(
                    variants + base_strings,
                    key=lambda t: t.position
                )

                for tag in all_tags:
                    # No translatable content found, move on
                    if not tag.content:
                        continue

                    key = self._get_key(string_tag, tag)
                    string = OpenString(
                        key,
                        tag.content,
                        context=section_tag.attrib[self.section_id_name],
                        order=order_counter.next(),
                    )
                    stringset.append(string)

                    # Move the transcriber accordingly, so that
                    # the content includes the hash placeholder
                    transcriber.copy_until(tag.text_position)
                    transcriber.add(string.template_replacement)
                    transcriber.skip(len(tag.content))

        # All translatable content has been handled,
        # now copy the rest of the content as is
        transcriber.copy_until(len(source))

        template = transcriber.get_destination()
        return template, stringset

    def compile(self, template, stringset, is_source=True, language_info=None):
        """Compile the given `template` by replacing all hash placeholders
        with the translations found in `stringset`.

        :param str template: the template that contains hash placeholders
            in the place of translatable text
        :param list stringset: a list of OpenString objects that represent
            all translations that should go into the template
        :param bool is_source: True if compiling for the source language,
            False otherwise
        :param dict language_info: a dictionary structured as:
            {'name': <language_name>, 'code': <language_code>}
        :return: the compiled string, which contains all translations
        :rtype: str
        :raise ParseError: if the root node is not found in `template`
        """
        root_tag_pos = self._get_root_node_pos(template)

        self.transcriber = Transcriber(template[root_tag_pos:])
        source = self.transcriber.source

        parsed = NewDumbXml(source)
        string_iterator = parsed.find_descendants(self.string_name)

        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()

        for string_tag in string_iterator:
            self._compile_string(string_tag)

        self.transcriber.copy_to_end()
        compiled = (
            template[:root_tag_pos] + self.transcriber.get_destination()
        )

        return compiled

    def _compile_string(self, string_tag):
        """Use the given `string_tag` in order to update the template,
        replacing all hash placeholders with the translated content.

        Updates the transcriber directly.

        :param NewNewDumbXml string_tag: an XML tag that may contain children
            with translatable content, e.g.
            <string key="..." attr2="..." attr3="...">
              <base>A string<base>
              <variant context="a">Another string</variant>
              <variant context="b">Yet another string</variant>
            </string>
        """
        # Copy until "<string key="..." ...>"
        self.transcriber.copy_until(string_tag.text_position)

        base_and_variants = string_tag.find_children(
            self.base_string_name, self.variant_string_name,
        )
        for translatable_str_node in base_and_variants:
            # Copy until "<base>" or "<variant>"
            self.transcriber.copy_until(translatable_str_node.text_position)

            # Only consume the current translation if the XML node has text
            if translatable_str_node.text:
                # Add the translation
                self.transcriber.add(self.next_string.string)
                self.next_string = self._get_next_string()

            # Skip the hash placeholder
            self.transcriber.skip_until(translatable_str_node.content_end)
            # Copy until "</base>" or "</variant>"
            self.transcriber.copy_until(translatable_str_node.tail_position)

    def _get_root_node_pos(self, string):
        """Return the position of the root node in the given string.

        :param str string: the content to search for the root node.
        :return: the integer position
        :rtype: int
        :raise ParseError: if the root node is not found
        """
        try:
            return string.index('<{}'.format(self.root_name))
        except ValueError:
            raise ParseError(
                'Root node "<{root}>" not found'.format(
                    root=self.root_name,
                )
            )

    def _get_key(self, string_tag, tag):
        """Return the key that corresponds to a given translatable string.

        Uses the attributes of the outer `string_tag` and the inner `tag`
        in order to construct a key.

        :param NewDumbXml string_tag: the outer XML tag that
            may contain various translatable strings
        :param NewDumbXml tag: the inner XML tag that contains
            one translatable string
        :return: the key of the corresponding translatable string
        :rtype: str
        """
        try:
            # Base string
            if tag.tag == self.base_string_name:
                return string_tag.attrib[self.string_key_name]

            # Variant
            else:
                return "{key}{separator}{variant_id}".format(
                    key=string_tag.attrib[self.string_key_name],
                    separator=COMPOSITE_KEY_SEPARATOR,
                    variant_id=tag.attrib[self.variant_string_context_name],
                )
        except KeyError:
            raise ParseError(
                'Missing "{key}" attribute in <{string}> node, '
                'parent of "<{tag.tag}>{tag.content}</{tag.tag}>"'.format(
                    key=self.string_key_name,
                    string=self.string_name,
                    tag=tag,
                )
            )

    def _get_next_string(self):
        """Get the next string from an iterable stringset.

        Return None if there is no other string.

        :return: An OpenString object or None if it has reached the end of
            the iterable
        """
        try:
            next_string = self.stringset.next()
        except StopIteration:
            next_string = None
        return next_string

