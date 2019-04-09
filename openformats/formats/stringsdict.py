from __future__ import absolute_import

import itertools
import re
from xml.sax import saxutils

import six

from openformats.utils.compat import ensure_unicode

from ..exceptions import RuleError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.xml import NewDumbXml
from ..utils.xmlutils import XMLUtils, reraise_syntax_as_parse_errors


class StringsDictHandler(Handler):
    """A handler class that parses and compiles `.stringsdict` files for iOS
    applications. The `.stringsdict` file is in XML format.

    `.stringsdict` file documentation can be found here:
    https://developer.apple.com/library/ios/documentation/MacOSX/Conceptual/BPInternational/StringsdictFileFormat/StringsdictFileFormat.html
    """

    name = "STRINGSDICT"
    extension = "stringsdict"

    EXTRACTS_RAW = False

    # Where to start parsing the file
    PARSE_START = "<dict"

    # Ignored or special keys
    KEY_FORMAT = 'NSStringLocalizedFormatKey'
    KEY_SPEC = 'NSStringFormatSpecTypeKey'
    KEY_VALUE = 'NSStringFormatValueTypeKey'

    # Regular expression for handling content with text and variables mixed
    VALUE_CONTENT_RE = r'(?P<prefix>[^@]*)%#@(?P<variable>\w+)@(?P<suffix>.*)'

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

    @reraise_syntax_as_parse_errors
    def parse(self, content, **kwargs):
        self.transcriber = Transcriber(content)
        self.order_counter = itertools.count()
        source = self.transcriber.source
        # Skip xml info declaration
        dict_tag_position = source.index(self.PARSE_START)

        parsed = NewDumbXml(source, dict_tag_position)
        XMLUtils.validate_no_text_characters(self.transcriber, parsed)
        XMLUtils.validate_no_tail_characters(self.transcriber, parsed)
        dict_iterator = parsed.find_children()
        stringset = []
        self.main_keys = set()
        self.existing_hashes = set()

        for key_tag in dict_iterator:
            dict_child = self._get_key_value(dict_iterator, key_tag)
            stringset.extend(
                self._handle_child_pairs(key_tag, dict_child)
            )

        # Finish copying and create template
        self.transcriber.copy_until(len(source))
        template = self.transcriber.get_destination()

        return template, stringset

    def _handle_child_pairs(self, key_tag, dict_tag):
        """Handles the <key> tag and its <dict> value tag.

        Note that in order to avoid splitting strings we perform the following
        inline-replacement:

            <key>NSStringLocalizedFormatKey</key>
            <string>Look! There %#@mouse@ there</string>
            <key>mouse</key>
            <dict>
                <key>NSStringFormatSpecTypeKey</key>
                <string>NSStringPluralRuleType</string>
                <key>NSStringFormatValueTypeKey</key>
                <string>d</string>
                <key>one</key>
                <string>is a mouse</string>
                <key>other</key>
                <string>are %d mice</string>
            </dict>

        Becomes:

            <key>NSStringLocalizedFormatKey</key>
            <string>%#@mouse@</string>
            <key>mouse</key>
            <dict>
                <key>NSStringFormatSpecTypeKey</key>
                <string>NSStringPluralRuleType</string>
                <key>NSStringFormatValueTypeKey</key>
                <string>d</string>
                <key>one</key>
                <string>Look! There is a mouse there</string>
                <key>other</key>
                <string>Look! There are %d mice there</string>
            </dict>

        This is necessary to avoid splitting sentences in Transifex, or omit
        parts of the translatable content. We reference this inline-replacement
        in the comments below as [1].

        :param key_tag: The <key> tag to be handled.
        :param dict_tag: The <dict> tag to be handled.
        :returns: A list containing the openstrings created. If no strings were
                    created the list is empty.
        """

        # The first key tag contains the main key
        main_key = self._handle_key(key_tag, main_key=True)
        dict_iterator = self._handle_dict(dict_tag)

        string_list = []
        # A helper variable to save the prefix and suffix needed for the
        # inline-replacement [1].
        text_extras = None

        for key_child in dict_iterator:
            # The second key contains the secondary key.
            secondary_key = self._handle_key(key_child)
            value_tag = self._get_key_value(dict_iterator, key_child)
            if secondary_key == self.KEY_FORMAT:
                matches = re.match(ensure_unicode(self.VALUE_CONTENT_RE),
                                   value_tag.content)
                if matches is not None:
                    # The prefix and the suffix are relative to the FIRST
                    # variable
                    text_extras = {
                        "variable": matches.group("variable"),
                        "prefix": matches.group("prefix"),
                        "suffix": matches.group("suffix"),
                    }
                # If the key is the one of the stringsdict defaults skip it
                continue

            openstring = self._handle_strings(
                value_tag,
                main_key,
                secondary_key,
                text_extras,
            )
            if openstring is not None:
                # If an openstring was created append it to the list
                string_list.append(openstring)
        return string_list

    def _handle_strings(self, dict_tag, main_key, secondary_key, extras):
        """Handles the <dict> tag that contains the strings.

        :param dict_tag: The <dict> tag containing the strings.
        :param main_key: The main key. Used as the openstring's name.
        :param secondary_key: The secondary key. Used as the openstring's
                                context.
        :param extras: A dictionary containing the `variable`, `prefix` and
                       `suffix` keys if we need to perform replacement [1],
                       `None` otherwise. This parameter is the same for each
                       call under the same main key.
        """
        dict_iterator = self._handle_dict(dict_tag)

        # If inline-replacement [1] is required, the first step is to remove
        # the prefix and the suffix from the original string.
        if extras is not None:
            # This isolates the part of the source file between the main key
            # and the plural rules, so we only replace the value of the
            # NSStringLocalizedFormatKey value
            text = self.transcriber.source[
                self.transcriber.ptr:dict_tag.position
            ]
            text = text.replace(u'<string>{}'.format(extras['prefix']),
                                u'<string>', 1)
            text = text.replace(u'{}</string>'.format(extras['suffix']),
                                u'</string>', 1)
            self.transcriber.add(text)
            self.transcriber.skip_until(dict_tag.position)
        else:
            self.transcriber.copy_until(dict_tag.position)

        # Save the line in which the plural rule starts to associate it with
        # the openstring object. This is used later for generating helpful
        # error messages
        line_number = self.transcriber.line_number
        if dict_tag.text is not None:
            self.transcriber.copy_until(
                dict_tag.text_position + len(dict_tag.text)
            )

        strings_dict = {}
        for key_tag in dict_iterator:
            key_content = self._handle_key(key_tag)
            value_tag = self._get_key_value(dict_iterator, key_tag)

            # Skip key-value pairs that don't include any translatable content
            if key_content in [self.KEY_SPEC, self.KEY_VALUE]:
                self.transcriber.copy_until(value_tag.tail_position)
                continue

            # Get rule number from the key content
            rule_number = self._validate_plural(key_content, key_tag)
            # If inline-replacement [1] is needed, and we now process the FIRST
            # variable, we apply the prefix and the suffix to each of the
            # plural rules
            if extras is not None and extras["variable"] == secondary_key:
                content = u"{prefix}{content}{suffix}".format(
                    prefix=extras["prefix"],
                    content=value_tag.content,
                    suffix=extras["suffix"],
                )
            else:
                content = value_tag.content
            strings_dict[rule_number] = content

            # If empty <string> tag keep it. It is either a placeholder which
            # should be kept or it is missing plurals and we will raise a
            # ParseError on self._create_string.
            if value_tag.content and value_tag.content.strip() != "":
                self.transcriber.skip_until(value_tag.end)
            else:
                self.transcriber.copy_until(value_tag.tail_position)

        openstring = self._create_string(
            main_key,
            strings_dict,
            secondary_key,
            dict_tag,
            line_number
        )

        if openstring is not None:
            self.transcriber.add(u''.join([
                key_tag.tail,
                self.PLACEHOLDER_KEY,
                key_tag.tail,
                self.PLACEHOLDER_STRING.format(
                    openstring.template_replacement
                ),
                value_tag.tail
            ]))
        self.transcriber.copy_until(dict_tag.end)
        return openstring

    def _create_string(self, main_key, strings_dict, secondary_key, tag,
                       line_number):
        """Validates and creates an OpenString.

        :main_key: The name of the OpenString.
        :strings_dict: A dictionary containing the plurals of the OpenString.
        :secondary_key: The context of the OpenString.
        :returns: An OpenString if one was created else None.
        """
        string_not_empty = XMLUtils.validate_not_empty_string(
            self.transcriber,
            strings_dict,
            tag,
            error_context={
                'line_number': line_number,
                'child_tag': 'string',
                'main_tag': tag.tag
            }
        )
        if string_not_empty:
            openstring = OpenString(
                main_key,
                strings_dict,
                context=secondary_key,
                order=next(self.order_counter),
                pluralized=True
            )
            return openstring
        return None

    def _validate_plural(self, plural_rule, key_tag):
        """Validates the plural rule.

        :param plural_rule: The string containing the plural rule.
        :key_tag: The <key> tag that contains the plural rule.
                    Used when validation fails to track the line number.
        :raises: ParseError when the plural_rule is invalid.
        :returns: An integer that matches the plural rule.
        """
        try:
            rule_number = self.get_rule_number(plural_rule)
        except RuleError:
            message = (
                u"The plural <key> tag on line {line_number} contains "
                u"an invalid plural rule: `{rule}`"
            )
            XMLUtils.raise_error(
                self.transcriber,
                key_tag,
                message,
                context={'rule': plural_rule}
            )

        return rule_number

    def _handle_key(self, key_tag, main_key=False):
        """Validates a <key> tag and returns it's content.

        :param key_tag: The <key> tag to validate.
        :param main_key: Specifies a key as main. If True it also validates
                            the key uniqueness.
        :raises: ParseError if the tag is not a <key>. Also raises a ParseError
                    if main_key is True and the key is not unique.
        :returns: A string containing the <key> tags content.
        """
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
                message = (
                    u"Duplicate main key ({main_key}) "
                    u"found on line {line_number}"
                )
                XMLUtils.raise_error(
                    self.transcriber,
                    key_tag,
                    message,
                    context={'main_key': key_content}
                )
            self.main_keys.add(key_content)

        return key_content

    def _handle_dict(self, dict_tag):
        """Validates a <dict> tag and returns it's children iterator.

        :param dict_tag: The <dict> tag to validate.
        :raises: ParseError if the tag is not <dict>.
        :returns: An iterator containing the children of the <dict> tag.
        """
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

    def compile(self, template, stringset, **kwargs):
        dict_tag_position = template.index(self.PARSE_START)

        self.transcriber = Transcriber(template[dict_tag_position:])
        source = self.transcriber.source

        parsed = NewDumbXml(source)
        dict_iterator = parsed.find_children(self.DICT)

        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()
        for dict_tag in dict_iterator:
            self._compile_dict(dict_tag)

        self.transcriber.copy_until(len(source))
        compiled = template[:dict_tag_position] +\
            self.transcriber.get_destination()

        return compiled

    def _compile_dict(self, dict_tag):
        """Compiles the `dict` tags that contains the translations.

        :param dict_tag: The main dict tag that contains the child dict tags
        which in turn contain the placeholders for the translations.
        If no translations are found for a child's placeholders
        the whole child dict is ommited.
        """

        if dict_tag.text is not None:
            self.transcriber.copy_until(
                dict_tag.text_position + len(dict_tag.text)
            )

        key_value_iterator = dict_tag.find_children()
        for key_tag in key_value_iterator:
            value_tag = self._get_key_value(key_value_iterator, key_tag)
            if value_tag.tag == self.DICT:
                placeholder_list = list(value_tag.find_children(
                    self.PLACEHOLDER_KEY_TAG, self.PLACEHOLDER_STRING_TAG
                ))
                should_compile = (
                    len(placeholder_list) and
                    XMLUtils.should_compile(
                        placeholder_list[-1],
                        self.next_string)
                )
                if should_compile:
                    placeholder_iterator = value_tag.find_children(
                        self.PLACEHOLDER_KEY_TAG, self.PLACEHOLDER_STRING_TAG
                    )
                    for placeholder_key in placeholder_iterator:
                        placeholder_value = self._get_key_value(
                            placeholder_iterator,
                            placeholder_key
                        )
                        # Copy until the placeholder_key
                        self.transcriber.copy_until(placeholder_key.position)
                        # Compile translation
                        self._compile_plural_string(
                            placeholder_key, placeholder_value
                        )
                        # Skip placeholder_key and placeholder_value
                        self.transcriber.skip_until(
                            placeholder_value.tail_position
                        )
                        # Copy the end to keep formating
                        self.transcriber.copy_until(
                            value_tag.tail_position
                        )

                else:
                    if len(placeholder_list):
                        self.transcriber.skip_until(value_tag.tail_position)
                    else:
                        self.transcriber.copy_until(value_tag.end)
            else:
                # Else copy until the end of the value tag
                self.transcriber.copy_until(value_tag.tail_position)
        self.transcriber.copy_until(dict_tag.end)

    def _compile_plural_string(self, placeholder_key, placeholder_value):
        """Replaces the placeholder tags with the translation strings.

        :param placeholder_key: The placeholder key tag.
        :param placeholder_value: The placeholder value tag.
        :NOTE: Assigns the self property `next_string` to the next OpenString.
        """
        to_add_list = []
        for rule, string in six.iteritems(self.next_string.string):
            to_add_list.extend([
                self.KEY_TEMPLATE.format(
                    rule_string=self.get_rule_string(rule)
                ),
                placeholder_key.tail,
                self.STRING_TEMPLATE.format(
                    plural_string=string
                ),
                placeholder_key.tail
            ])
        self.transcriber.add(u''.join(to_add_list[:-1]))
        self.next_string = self._get_next_string()

    def _get_next_string(self):
        """Gets the next string from stringset itterable.

        :returns: An openstring object or None if it has reached the end of
                    the itterable.
        """
        try:
            next_string = next(self.stringset)
        except StopIteration:
            next_string = None
        return next_string

    """ Util methods """

    def _get_key_value(self, iterator, key_tag):
        """Gets the value of the current <key> tag.

        :param iterator: The iterator that contains <key> tag's value.
        """
        try:
            value_tag = next(iterator)
        except StopIteration:
            message = (
                u"Did not find a value for the <key> tag on "
                u"line {line_number}"
            )
            XMLUtils.raise_error(
                self.transcriber,
                key_tag,
                message,
            )
        return value_tag

    @staticmethod
    def escape(string):
        return saxutils.escape(string)

    @staticmethod
    def unescape(string):
        return saxutils.unescape(string)
