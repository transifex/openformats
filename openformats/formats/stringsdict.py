from __future__ import absolute_import

import itertools

from ..utils.xmlutils import XMLUtils
from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..utils.xml import NewDumbXml, DumbXmlSyntaxError
from ..exceptions import RuleError

from ..transcribers import Transcriber


class StringsDictHandler(Handler):
    """A handler class that parses and compiles `.stringsdict` files for iOS
    applications. The `.stringsdict` file is in XML format.

    `.stringsdict` file documentation can be found here:
    https://developer.apple.com/library/ios/documentation/MacOSX/Conceptual/BPInternational/StringsdictFileFormat/StringsdictFileFormat.html
    """

    name = "STRINGSDICT"
    extension = "xml"

    EXTRACTS_RAW = False

    # Where to start parsing the file
    PARSE_START = "<dict"

    # Ignored keys
    KEY_FORMAT = 'NSStringLocalizedFormatKey'
    KEY_SPEC = 'NSStringFormatSpecTypeKey'
    KEY_VALUE = 'NSStringFormatValueTypeKey'

    # Placeholders
    PLACEHOLDER_KEY_TAG = 'tx_awesome_key_tag'
    PLACEHOLDER_KEY = '<tx_awesome_key_tag></tx_awesome_key_tag>'
    PLACEHOLDER_STRING_TAG = 'tx_awesome_string_tag'
    PLACEHOLDER_STRING = '<tx_awesome_string_tag>{}</tx_awesome_string_tag>'

    # Complile templates
    KEY_TEMPLATE = u'<key>{rule_string}</key>'
    STRING_TEMPLATE = u'<string>{plural_string}</string>'

    # Relevant tags
    STRING = "string"
    DICT = "dict"
    KEY = "key"

    """ Parse Methods """

    def parse(self, content):
        self.transcriber = Transcriber(content)
        self.order_counter = itertools.count()
        source = self.transcriber.source
        # Skip xml info declaration
        resources_tag_position = source.index(self.PARSE_START)

        try:
            parsed = NewDumbXml(source, resources_tag_position)
            XMLUtils.validate_no_text_characters(self.transcriber, parsed)
            XMLUtils.validate_no_tail_characters(self.transcriber, parsed)
            dict_iterator = parsed.find_children()
            stringset = []
            self.main_keys = set()
            self.existing_hashes = set()

            for key_tag in dict_iterator:
                dict_child = self._get_key_value(dict_iterator)
                stringset.extend(
                    self._handle_child_pairs(key_tag, dict_child)
                )

        except DumbXmlSyntaxError, e:
            raise ParseError(unicode(e))

        # Finish copying and create template
        self.transcriber.copy_until(len(source))
        template = self.transcriber.get_destination()

        return template, stringset

    def _handle_child_pairs(self, key_tag, dict_tag):
        """Handles the <key> tag and its <dict> value tag.

        :param key_tag: The <key> tag to be handled.
        :param dict_tag: The <dict> tag to be handled.
        :returns: A list containing the openstrings created. If no strings were
                    created the list is empty.
        """
        # The first key tag contains the main key
        main_key = self._handle_key(key_tag, main_key=True)
        dict_iterator = self._handle_dict(dict_tag)

        string_list = []
        for key_child in dict_iterator:
            # The second key contains the secondary key.
            secondary_key = self._handle_key(key_child)
            value_tag = self._get_key_value(dict_iterator)
            if secondary_key == self.KEY_FORMAT:
                # If the key is the one of the stringsdict defaults skip it
                continue

            openstring = self._handle_strings(
                value_tag,
                main_key,
                secondary_key
            )
            if openstring is not None:
                # If an openstring was created append it to the list
                string_list.append(openstring)
        return string_list

    def _handle_strings(self, dict_tag, main_key, secondary_key):
        """Handles the <dict> tag that contains the strings.

        :param dict_tag: The <dict> tag containing the strings.
        :param main_key: The main key. Used as the openstring's name.
        :param secondary_key: The secondary key. Used as the openstring's
                                context.
        """
        dict_iterator = self._handle_dict(dict_tag)

        strings_dict = {}
        for key_tag in dict_iterator:
            key_content = self._handle_key(key_tag)
            value_tag = self._get_key_value(dict_iterator)

            if key_content in [self.KEY_SPEC, self.KEY_VALUE]:
                # If key in stringsdict's default keys skip it
                self.transcriber.copy_until(value_tag.tail_position)
                continue

            # Get rule number from the key content
            rule_number = self._validate_plural(key_content, key_tag)
            strings_dict[rule_number] = value_tag.content
            self.transcriber.skip_until(value_tag.tail_position)

        openstring = self._create_string(
            main_key,
            strings_dict,
            secondary_key,
            dict_tag
        )

        if openstring is not None:
            # In case we ended with an ignored key
            self.transcriber.skip_until(value_tag.end)
            self.transcriber.add(
                key_tag.tail +
                self.PLACEHOLDER_KEY +
                key_tag.tail +
                self.PLACEHOLDER_STRING.format(
                    openstring.template_replacement
                )
                + value_tag.tail
            )
        else:
            # If no strings exist in <dict> tag assume placeholder and continue
            self.transcriber.copy_until(value_tag.end)
        return openstring

    def _create_string(self, main_key, strings_dict, secondary_key, tag):
        """Validates and creates an OpenString.

        :main_key: The name of the OpenString.
        :strings_dict: A dictionary containing the plurals of the OpenString.
        :secondary_key: The context of the OpenString.
        :returns: An OpenString if one was created else None.
        """
        string_not_empty = XMLUtils.validate_not_empty_string(
            self.transcriber,
            strings_dict,
            tag
        )
        if string_not_empty:
            openstring = OpenString(
                main_key,
                strings_dict,
                context=secondary_key,
                order=self.order_counter.next(),
                pluralized=True
            )
            return openstring
        return None

    def _validate_plural(self, plural_string, key_tag):
        try:
            rule_number = self.get_rule_number(plural_string)
        except RuleError:
            message = (
                u"The plural <key> tag on line {line_number} contains "
                u"an invalid plural rule: `{rule}`"
            )
            XMLUtils.raise_error(
                self.transcriber,
                key_tag,
                message,
                context={'rule': plural_string}
            )

        return rule_number

    def _handle_key(self, key_tag, main_key=False):
        if key_tag.tag != self.KEY:
            message = (
                u"Was expecting <key> tag but found <{tag}> tag "
                u"on line {line_number}"
            )
            XMLUtils.raise_error(
                self.transcriber,
                key_tag,
                message,
                context={'tag': key_tag.tag}
            )

        key_content = key_tag.content
        if main_key:
            if key_content in self.main_keys:
                message = u"Duplicate main key found on line {line_number}"
                XMLUtils.raise_error(
                    self.transcriber,
                    key_tag,
                    message
                )
            self.main_keys.add(key_content)

        return key_content

    def _handle_dict(self, dict_tag):
        if dict_tag.tag != self.DICT:
            message = (
                u"Was expecting <dict> tag but found <{tag}> tag on line "
                u"{line_number}"
            )
            XMLUtils.raise_error(
                self.transcriber,
                dict_tag,
                message,
                context={'tag': dict_tag.tag}
            )
        return dict_tag.find_children()

    """ Compile Methods """

    def compile(self, template, stringset):
        resources_tag_position = template.index(self.PARSE_START)

        self.transcriber = Transcriber(template[resources_tag_position:])
        source = self.transcriber.source

        parsed = NewDumbXml(source)
        dict_iterator = parsed.find_children(self.DICT)

        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()
        for dict_tag in dict_iterator:
            self._compile_dict(dict_tag)

        self.transcriber.copy_until(len(source))
        compiled = template[:resources_tag_position] +\
            self.transcriber.get_destination()

        return compiled

    def _compile_dict(self, dict_tag):
        """Compiles the `dict` tags that contains the translations.

        :param dict_tag: The main dict tag that contains the child dict tags
        which in turn contain the placeholders for the translations.
        If no translations are found for a child's placeholders
        the whole child dict is ommited.
        """
        self.transcriber.copy_until(dict_tag.position)
        key_value_iterator = dict_tag.find_children()
        for key_tag in key_value_iterator:
            value_tag = self._get_key_value(key_value_iterator)
            if value_tag.tag == self.DICT:
                # If child dict is found find the placeholders
                placeholder_iterator = value_tag.find_children(
                    self.PLACEHOLDER_KEY_TAG, self.PLACEHOLDER_STRING_TAG
                )
                for placeholder_key in placeholder_iterator:
                    placeholder_value = self._get_key_value(
                        placeholder_iterator
                    )
                    should_compile = (
                        XMLUtils.should_compile(
                            placeholder_value,
                            self.next_string)
                    )
                    if should_compile:
                        # If we have translation for the placeholder compile it
                        self._compile_plural_string(
                            placeholder_key, placeholder_value
                        )
                        self.transcriber.copy_until(value_tag.tail_position)
                    else:
                        # Else skip the dict tag
                        self.transcriber.skip_until(value_tag.end)
            else:
                # Else copy until the end of the value tag
                self.transcriber.copy_until(value_tag.end)

    def _compile_plural_string(self, placeholder_key, placeholder_value):
        """Replaces the placeholder tags with the translation strings.

        :param placeholder_key: The placeholder key tag.
        :param placeholder_value: The placeholder value tag.
        :NOTE: Assigns the self property `next_string` to the next OpenString.
        """
        self.transcriber.copy_until(placeholder_key.position)
        string_list = self.next_string.string.items()
        last_index = len(string_list) - 1
        for i, (rule, string) in enumerate(string_list):
            self.transcriber.add(
                self.KEY_TEMPLATE.format(
                    rule_string=self.get_rule_string(rule)
                ) +
                placeholder_key.tail +
                self.STRING_TEMPLATE.format(
                    plural_string=string
                ) +
                (placeholder_key.tail if i != last_index else '')
            )

        self.transcriber.skip_until(placeholder_value.tail_position)
        self.next_string = self._get_next_string()

    def _get_next_string(self):
        """Gets the next string from stringset itterable.

        :returns: An openstring object or None if it has reached the end of
                    the itterable.
        """
        try:
            next_string = self.stringset.next()
        except StopIteration:
            next_string = None
        return next_string

    """ Util methods """

    @staticmethod
    def _get_key_value(iterator):
        """Gets the value of the current <key> tag.

        :param iterator: The iterator that contains <key> tag's value.
        """
        try:
            value_tag = iterator.next()
        except StopIteration:
            raise ParseError()
        return value_tag
