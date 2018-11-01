
import re
import pyparsing

from openformats.handlers import Handler
from openformats.exceptions import ParseError


class ICUString(object):
    """Represents a string that follows the ICU format."""

    def __init__(self, key, string_info, pluralized):
        """Constructor.

        :param str key: the ID of the string
        :param list string_info: a list of tuples that contains all plural strings
            together with their plurality rule string, formatted as:
            [(plurality_str, string_with_braces), ...], e.g.
            [
              ('zero', 'No tables'),
              ('one', '{cnt} table'),
              ('other': '{cnt} tables')
            ]
        :param bool pluralized: True if the string is pluralized,
            False otherwise
        """
        self.key = key
        self.string_info = string_info
        self.pluralized = pluralized
        self.value_position = None
        self.current_position = None
        self.string_to_replace = None

    @property
    def strings_by_rule(self):
        """A dictionary that contains all plural strings, grouped
        by their integer plural rule.

        Plural strings do not include the enclosing braces ({}).

        Formatted as `{ plural_rule: string_without_braces, ...}`,
        e.g. {0: 'No tables', 1: '{cnt} table', 5: '{cnt} tables'}

        :rtype: dict
        """
        return {
            Handler.get_rule_number(plurality_str): content[1:-1]
            for plurality_str, content in self.string_info
        }

    def __repr__(self):
        return 'ICUString key={}, string_to_replace={}, pluralized={}, ' \
               'string_info={}, value_position={}, current_position={}'.format(
                self.key,
                self.string_to_replace,
                self.pluralized,
                repr(self.string_info),
                self.value_position,
                self.current_position,
                )


class ICUHelper(object):
    """Knows how to parse and compile strings that follow the ICU standard.

    Only a small subset of the standard is currently supported,
    namely plurals.
    """

    PLURAL_ARG = 'plural'
    PLURAL_KEYS_STR = ' '.join(Handler._RULES_ATOI.keys())

    @classmethod
    def parse(cls, key, value, value_position):
        """
        Parse a string that follows a subset of the the ICU message format
        and return an ICUString object.

        For the time being, only the plurals format is supported.
        If `value` doesn't match the proper format, it will return None.
        This method will also update the transcriber accordingly.

        Note: if we want to support more ICU features in the future,
        this would probably have to be refactored.

        :param key: the string key
        :param value: the serialized string that has all the content,
            formatted like this (whitespace irrelevant):
            { item_count, plural,
                one { You have {file_count} file. }
                other { You have {file_count} files. }
            }
        :return: an ICUString object with all parsed information or None if
            the string is not in the supported ICU format
        :rtype: ICUString
        """
        matches = re.match(
            ur'\s*{\s*([A-Za-z-_\d]+)\s*,\s*([A-Za-z_]+)\s*,\s*(.*)}\s*',
            value,
        )
        if not matches:
            return None

        keyword, argument, serialized_strings = matches.groups()

        if argument == cls.PLURAL_ARG:
            return cls._parse_pluralized_string(
                key, keyword, value, value_position,
                serialized_strings
            )

        return None

    @classmethod
    def serialize_pluralized_string(cls, pluralized_string, delimiter=' '):
        """
        Serialize the given pluralized_string into a suitable format
        for adding it to the document in the compilation phase.

        This essentially concatenates the plural rule strings and translations
        for each rule into one string.

        For example:
        ' ' delimiter => 'one { {cnt} chip. } other { {cnt} chips. }'
        '\n' delimiter => 'one { {cnt} chip. }\nother { {cnt} chips. }'

        :param pluralized_string: an OpenString that is pluralized
        :param delimiter: a string to use for separating entries
        :return: a string
        """
        plural_list = [
            u'{} {{{}}}'.format(
                Handler.get_rule_string(rule),
                translation
            )
            for rule, translation in pluralized_string.string.iteritems()
        ]
        return delimiter.join(plural_list)

    @classmethod
    def _parse_pluralized_string(cls, key, keyword, value, value_position,
                                 serialized_strings):
        """
        Parse `serialized_strings` in order to find and return all included
        pluralized strings.

        :param key: the string key
        :param keyword: the message key, e.g. `item_count` in:
            '{ item_count, plural, one { {cnt} tip } other { {cnt} tips } }'
        :param serialized_strings: the plurals in the form of multiple
            occurrences of the following (whitespace irrelevant):
            '<plurality_rule_str> { <content> }',
            e.g. 'one { I ate {cnt} apple. } other { I ate {cnt} apples. }'
        :return: A pluralized ICUString instance or None
        """
        # The official plurals format supports defining an integer instead
        # of the name of the plural rule, using a syntax like "=1" or "=2"
        # We do not support this at the moment, but we want to have these
        # strings be handled as non pluralized.
        equality_item = (
            pyparsing.Literal('=') + pyparsing.Word(pyparsing.alphanums) +
            pyparsing.nestedExpr('{', '}')
        )
        equality_matches = pyparsing.originalTextFor(equality_item)\
            .searchString(serialized_strings)

        # If any match is found using this syntax, do not parse this
        # as pluralized
        if len(equality_matches) > 0:
            return None

        # Each item should be like '<proper_plurality_rule_str> {<content>}'
        # Nested braces ({}) inside <content> are allowed.
        #
        # Note:
        # Be sure to ignore single quotes ('), otherwise strings that include
        # one quote in one plural and another one in another plural, will be
        # parsed as pluralized but with less rules than they actually have.
        # (matching will actually include content from multiple rules combined,
        # instead of separating the content per rule). This seems like a
        # pyparsing bug. Any other character that could be a potential
        # separator doesn't seem cause any problem.
        valid_plural_item = (
            pyparsing.oneOf(cls.PLURAL_KEYS_STR) +
            pyparsing.nestedExpr('{', '}', ignoreExpr=pyparsing.Literal("'"))
        )

        # We need to make sure that the plural rules are valid.
        # Therefore, we also match any <alphanumeric> {<content>} string
        # and see if there are differences compared to the valid results
        # we got above.
        any_plural_item = (
            pyparsing.Word(pyparsing.alphanums) +
            pyparsing.nestedExpr('{', '}', ignoreExpr=pyparsing.Literal("'"))
        )

        all_matches = pyparsing.originalTextFor(any_plural_item).searchString(
            serialized_strings
        )
        cls._validate_plural_content_format(
            key, value, serialized_strings, all_matches
        )

        # Create a list of serialized plural items, e.g.:
        # ['one { I ate {count} apple. }']
        valid_matches = pyparsing.originalTextFor(valid_plural_item)\
            .searchString(serialized_strings)

        # Make sure the plurality rules are valid
        # If not, an error will be raised
        if len(valid_matches) != len(all_matches):
            cls._handle_invalid_plural_format(
                serialized_strings, any_plural_item, key, value
            )

        # Create a list of tuples [(plurality_str, content_with_braces)]
        all_strings_list = [
            cls._parse_plural_content(match[0])
            for match in valid_matches
        ]

        icu_string = ICUString(key, all_strings_list, pluralized=True)

        # ICU's message format contains an arbitrary string at the beginning.
        # We need to include that in the template, because otherwise we won't
        # have enough information to recreate it in the compilation phase.
        # e.g. in { item_count, plural, other {You have {file_count} files.} }
        # `item_count` is a string set by the user, it's not a standard.
        # We'll keep everything up to the comma that follows the 'plural'
        # argument.
        current_pos = value.index(keyword) + len(keyword)
        current_pos = value.index(cls.PLURAL_ARG, current_pos)\
            + len(cls.PLURAL_ARG)
        current_pos = value.index(',', current_pos) + len(',')

        # We want to preserve the original document as much as possible,
        # so we'll add any whitespace between the comma and the
        # first plurality rule, e.g. 'one'
        current_pos = value.index(all_strings_list[0][0], current_pos)

        # Also include whitespace between the last two closing braces
        second_last_closing_brace = value.rfind('}', 0, value.rfind('}')) + 1
        string_to_replace = value[current_pos:second_last_closing_brace]

        icu_string.value_position = value_position
        icu_string.current_position = current_pos
        icu_string.string_to_replace = string_to_replace

        return icu_string

    @classmethod
    def _validate_plural_content_format(cls, key, value, serialized_strings,
                                        all_matches):
        """
        Make sure the serialized content is properly formatted
        as one or more pluralized strings.
        :param key: the string key
        :param value: the whole value of the string, e.g.
            { item_count, plural, zero {...} one {...} other {...}}
        :param serialized_strings: the part of the value that holds the
            string information only, e.g.
            zero {...} one {...} other {...}
        :param all_matches: a pyparsing element that matches all strings
            formatted like '<alphanumeric> {...}'

        :raise ParseError: if the given string has an invalid structure
        """
        # Replace all matches with spaces in the given string.
        remaining_str = serialized_strings
        for match in all_matches:
            remaining_str = remaining_str.replace(match[0], '')

        # Then make sure all whitespace is removed as well
        # Special characters may be present with double backslashes,
        # e.g. \\n
        remaining_str = remaining_str.replace('\\n', '\n')\
            .replace('\\t', '\t')\
            .strip()

        if len(remaining_str) > 0:
            raise ParseError(
                'Invalid format of pluralized entry '
                'with key: "{}", serialized translations: "{}". '
                'Could not parse the string at or near the following chunk: "{}". '
                'It contains either invalid braces ("{{", "}}") '
                'or invalid characters.'.format(
                    key, serialized_strings, remaining_str
                )
            )

    @classmethod
    def _handle_invalid_plural_format(cls, serialized_strings,
                                      any_plural_item, key, value):
        """
        Raise a descriptive ParseError exception when the serialized
        translation string of a plural string is not properly formatted.

        :param serialized_strings:
        :param any_plural_item: a forgiving pyparsing element that matches all
            strings formatted like '<alphanumeric> {...}'

        :raise: ParseError
        """
        all_matches = any_plural_item.searchString(serialized_strings)
        all_keys = [match[0] for match in all_matches]

        invalid_rules = [
            rule for rule in all_keys
            if rule not in Handler._RULES_ATOI.keys()
        ]
        raise ParseError(
            'Invalid plural rule(s): {} in pluralized entry '
            'with key: {}, value: "{}". '
            'Allowed values are: {}'.format(
                ', '.join(invalid_rules),
                key, value,
                ', '.join(Handler._RULES_ATOI.keys())
            )
        )

    @classmethod
    def _parse_plural_content(cls, string):
        # Find the content inside the brackets
        opening_brace_index = string.index('{')
        content = string[opening_brace_index:]

        # Find the plurality type (zero, one, etc)
        plurality = string[:opening_brace_index].strip()

        return plurality, content
