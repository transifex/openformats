
import re
import pyparsing

from openformats.handlers import Handler
from openformats.exceptions import ParseError


NUMERIC_RULES = ['=0', '=1', '=2']
SUPPORTED_PLURAL_RULES = Handler._RULES_ATOI.keys() + NUMERIC_RULES
RULE_MAPPING = {
    '=0': 'zero',
    '=1': 'one',
    '=2': 'two',
}

# Corresponds to the `=N` syntax, e.g. `=1`
PLURAL_FORMAT_STRING = 0
# Corresponds to the `<rule_str>` syntax, e.g. `one`
PLURAL_FORMAT_NUMERIC = 1


def normalize_plural_rule(rule_str):
    """Returns the equivalent rule name as 'one', 'two', etc.

    ICU supports plurality rules in the form of =N (e.g. =2).
    This method converts any such string to its equivalent "word" form.
    >>> normalize_plural_rule('=0') == 'zero'
    >>> normalize_plural_rule('zero') == 'zero'

    :param str rule_str: the name of the plural rule, e.g. '=1' or 'zero'
    :return: the word form of the plural rule
    :rtype: str
    """
    return RULE_MAPPING.get(rule_str, rule_str)


class ICUString(object):
    """Represents a string that follows the ICU format."""

    def __init__(self, key, string_info, pluralized):
        """Constructor.

        :param str key: the ID of the string
        :param list string_info: a list of tuples that contains all
            plural strings together with their plurality rule string,
            formatted as:
            [(plurality_str, string_with_braces), ...], e.g.
            [
              ('zero', 'No tables'),
              ('one', '{cnt} table'),
              ('other', '{cnt} tables')
            ]
        :param bool pluralized: True if the string is pluralized,
            False otherwise
        """
        self.key = key
        self.string_info = string_info
        self.pluralized = pluralized
        self.current_position = None
        self.string_to_replace = None

    @property
    def strings_by_rule(self):
        """A dictionary that contains all plural strings, grouped
        by their integer plural rule.

        Plural strings do not include the enclosing outer braces ({}).

        Formatted as `{ plural_rule: string_without_braces, ...}`,
        e.g. {0: 'No tables', 1: '{cnt} table', 5: '{cnt} tables'}

        :rtype: dict
        """
        return {
            Handler.get_rule_number(
                normalize_plural_rule(plurality_str)
            ): content[1:-1]
            for plurality_str, content in self.string_info
        }

    @property
    def syntax_by_rule(self):
        """A dictionary of the plural syntax that corresponds to each plural rule.

        There are 2 available ways to format a plural string in ICU format:
        numeric (e.g. `=1`) and string (e.g. `one`).

        Depending on the plurality string that is stored per each plural rule,
        this dictionary will contain the proper syntax for each plural rule,
        to be used when rendering the strings in a serialized ICU format.

        Example:
        {
          1: PLURAL_FORMAT_NUMERIC,  # =1
          2: PLURAL_FORMAT_NUMERIC,  # =2
          5: PLURAL_FORMAT_STRING,   # other
        }

        :rtype: dict
        """
        return {
            Handler.get_rule_number(
                normalize_plural_rule(plurality_str)
            ): (
                PLURAL_FORMAT_NUMERIC if plurality_str in RULE_MAPPING.keys()
                else PLURAL_FORMAT_STRING
            )
            for plurality_str, content in self.string_info
        }

    def __repr__(self):
        format_str = 'ICUString key={}, string_to_replace={}, pluralized={}, ' \
            'string_info={}, current_position={}'

        return format_str.format(
            self.key,
            self.string_to_replace,
            self.pluralized,
            repr(self.string_info),
            self.current_position,
        )


class ICUParser(object):
    """Knows how to parse strings that follow the ICU standard.

    Currently only plurals are supported.

    Examples:
    >>> parser = ICUParser()
    >>> icu_str = parser.parse('key', '{cnt, plural, one {table} other {tables}}')
    >>> # returns an ICUString object

    >>> parser = ICUParser()
    >>> icu_str = parser.parse('key', '{cnt, select, one {table} other {tables}}')
    >>> # returns None

    >>> parser = ICUParser()
    >>> icu_str = parser.parse('key', '{cnt, plural, =1 {table} other {tables}}')
    >>> # returns an ICUString object

    >>> parser = ICUParser(allow_numeric_plural_values=False)
    >>> icu_str = parser.parse('key', '{cnt, plural, =1 {table} other {tables}}')
    >>> # returns None

    >>> parser = ICUParser()
    >>> icu_str = parser.parse('key', '{cnt, plural, foo {table} other {tables}}')
    >>> # raises ParseError
    """

    PLURAL_ARG = 'plural'

    def __init__(self, allow_numeric_plural_values=True):
        """Constructor.

        If you are planning to use the ICU parser for a file format
        that supports the `=N` plural syntax, you need to set
        `allow_numeric_plural_values=True` (or leave it as is).
        Otherwise, if you are planning to use the ICU parser
        for a file format that handles strings with the `=N` syntax
        as non-pluralized, you should use `allow_numeric_plural_values=False`
        instead.

        :param bool allow_numeric_plural_values: if True or missing,
            the `=N` syntax will yield a valid pluralized ICUString,
            otherwise if there is such a syntax, and this parameter
            is False, a ParseError will be raised on parse()
        """
        self.allow_numeric_plural_values = allow_numeric_plural_values

    def parse(self, key, value):
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
        :raise ParseError: if the given string looks a lot like
            an ICU plural string but has an invalid structure
        """
        matches = re.match(
            ur'\s*{\s*([A-Za-z-_\d]+)\s*,\s*([A-Za-z_]+)\s*,\s*(.*)}\s*',
            value,
        )
        if not matches:
            return None

        keyword, argument, serialized_strings = matches.groups()

        if argument == ICUParser.PLURAL_ARG:
            return self._parse_pluralized_string(
                key, keyword, value, serialized_strings,
            )

        return None

    def _parse_pluralized_string(self, key, keyword, value, serialized_strings):
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
        if not self.allow_numeric_plural_values:
            # The official ICU standard supports the numeric (`=N`)
            # syntax notation. Instead of providing the name of the plural
            # rule, you can define an integer rule instead, e.g. "=1" or "=2".
            # The JSON parser does not currently support this syntax,
            # and instead handles these strings as non-pluralized.
            # The `allow_numeric_plural_values` variable exists
            # for backwards compatibility: if it's True, and the string is
            # following the =N syntax, we need to stop parsing this string
            # as pluralized and return None.
            equality_item = (
                pyparsing.oneOf(NUMERIC_RULES) +
                pyparsing.nestedExpr('{', '}', ignoreExpr=pyparsing.Literal("'"))
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
            pyparsing.oneOf(SUPPORTED_PLURAL_RULES) +
            pyparsing.nestedExpr('{', '}', ignoreExpr=pyparsing.Literal("'"))
        )

        # Create a list of serialized plural items, e.g.:
        # ['one { I ate {count} apple. }']
        valid_matches = pyparsing.originalTextFor(valid_plural_item)\
            .searchString(serialized_strings)

        # We need to make sure that the plural rules are valid.
        # Therefore, we also match any <alphanumeric> {<content>} string
        # and see if there are differences compared to the valid results
        # we got above.
        any_plural_item = (
            pyparsing.Word('=' + pyparsing.alphanums) +
            pyparsing.nestedExpr('{', '}', ignoreExpr=pyparsing.Literal("'"))
        )

        all_matches = pyparsing.originalTextFor(any_plural_item).searchString(
            serialized_strings
        )

        self._validate_plural_content_format(
            key, serialized_strings, all_matches,
        )

        # Make sure the plurality rules are valid
        # If not, an error will be raised
        if len(valid_matches) != len(all_matches):
            self._handle_invalid_plural_format(
                serialized_strings, any_plural_item, key, value
            )

        # Create a list of tuples [(plurality_str, content_with_braces)]
        all_strings_list = [
            self._parse_plural_content(match[0])
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
        current_pos = value.index(ICUParser.PLURAL_ARG, current_pos)\
            + len(ICUParser.PLURAL_ARG)
        current_pos = value.index(',', current_pos) + len(',')

        # We want to preserve the original document as much as possible,
        # so we'll add any whitespace between the comma and the
        # first plurality rule, e.g. 'one'
        current_pos = value.index(all_strings_list[0][0], current_pos)

        # Also include whitespace between the last two closing braces
        second_last_closing_brace = value.rfind('}', 0, value.rfind('}')) + 1
        string_to_replace = value[current_pos:second_last_closing_brace]

        icu_string.current_position = current_pos
        icu_string.string_to_replace = string_to_replace

        return icu_string

    def _validate_plural_content_format(self, key, serialized_strings, all_matches):
        """
        Make sure the serialized content is properly formatted
        as one or more pluralized strings.
        :param key: the string key
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
                'with key: "{key}", serialized translations: "{trans_str}". '
                'Could not parse the string at or near '
                'the following chunk: "{chunk}". '
                'It contains either invalid braces ("{{", "}}") '
                'or invalid characters.'.format(
                    key=key,
                    trans_str=serialized_strings,
                    chunk=remaining_str,
                )
            )

    def _handle_invalid_plural_format(self, serialized_strings,
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
            'Invalid plural rule(s): "{}" in pluralized entry '
            'with key: {}, value: "{}". '
            'Allowed values are: {}'.format(
                ', '.join(invalid_rules),
                key, value,
                ', '.join(Handler._RULES_ATOI.keys())
            )
        )

    @staticmethod
    def _parse_plural_content(string):
        # Find the content inside the brackets
        opening_brace_index = string.index('{')
        content = string[opening_brace_index:]

        # Find the plurality type (zero, one, etc)
        plurality = string[:opening_brace_index].strip()

        return plurality, content


class ICUCompiler(object):
    """Contains helper functions for serializing pluralized strings
    into ICU message format."""

    def serialize_strings(self, hashes_by_rule, delimiter=' ', syntax_by_rule=None):
        """Serialize the given pluralized_string into a suitable format
        for adding it to the document in the compilation phase.

        This essentially concatenates the plural rule strings and translations
        for each rule into one string.

        For example:
        delimiter = ' ' => 'one { {cnt} chip. } other { {cnt} chips. }'
        delimiter = '\n' => 'one { {cnt} chip. }\nother { {cnt} chips. }'

        If `syntax_by_rule` is provided, the formatting will use the
        corresponding syntax, e.g.:
        > syntax_by_rule = {1: PLURAL_FORMAT_NUMERIC, 5: PLURAL_FORMAT_STRING}
        > delimiter = ' '
        >   => '=1 {{cnt} table} other {{cnt} tables}'

        :param dict hashes_by_rule: a dictionary with one hash placeholder
            per each plural rule, e.g.
            {
               1: 'a2eb8a66695435a29ee61d5df781679b_pl_0',
               5: 'a2eb8a66695435a29ee61d5df781679b_pl_1',
            }
        :param str delimiter: a string to use for separating entries
        :param dict syntax_by_rule: a dictionary that associates
            a plural format (numeric or strings) with each rule,
            e.g. {1: PLURAL_FORMAT_NUMERIC, 5: PLURAL_FORMAT_STRING}
        :return: a string with all plural rules and their
            corresponding strings
        :rtype: str
        """
        syntax_by_rule = syntax_by_rule or {}
        plural_list = [
            u'{rule} {{{translation}}}'.format(
                rule=(
                    u'={}'.format(rule)
                    if syntax_by_rule.get(rule) == PLURAL_FORMAT_NUMERIC
                    else Handler.get_rule_string(rule)
                ),
                translation=translation,
            )
            for rule, translation in hashes_by_rule.iteritems()
        ]
        return delimiter.join(plural_list)

    def serialize_placeholder_string(self, icu_string, plural_rules):
        """Serialize the given ICUString, that should contain hash
        placeholders, for all provided plural rules.

        Returns a string that contains only the translatable part
        of the ICU string, for all plural rules provided, i.e.
        it does not include any other part of the string, such as the
        initial declaration, e.g. '{count, plural, '

        It only works well if the ICUString content is indeed
        the hash placeholders of a pluralized string, because it makes
        certain assumptions about how each plural string looks like.

        It takes into account any custom syntax guidelines that exist in
        the ICUString object. For example, if for rule 'one'
        the guideline is to use a numeric form, '=1' will be used
        when serializing.

        In other words, what this method does is to create a serialized
        version of placeholder hashes, following the ICU plural format,
        for a specific set of plural rules. This works regardless
        how many plural rules are found in `icu_string` (source language
        string) and how many languages are found in `plural_rules`
        (target language). The reason this works is that all placeholders
        follow the same format, which is a hash, following by `_pl_<rule>`.
        So, if we know one placeholder, we can generate the placeholders
        for any rule set.

        Examples:
        > For a language with [1, 3, 4, 5] rules, and a hash that
        > starts with 'a3b3_pl_', returns:
        > 'one {a3b3_pl_0} few {a3b3_pl_1} many {a3b3_pl_2} other {a3b3_pl_3}'

        > For a language with [1, 2, 5] rules and numeric syntax in
        > 'one' and 'two' rules, and a hash that starts with '62cc_pl_',
        > returns:
        > '=1 {62cc_pl_0} =2 {62cc_pl_1} other {62cc_pl_2}'

        :param ICUString icu_string: the string to serialize
        :param list plural_rules: a list of the numeric plurality rules
            to serialize for
        :return: the serialize string
        :rtype: str
        """
        # Get a dictionary of all hash placeholders, one per each rule
        # of the target language
        hashes_by_rule = ICUCompiler._create_placeholders_by_rule(
            icu_string, plural_rules,
        )

        # Render all hashes into an ICU plural format,
        # e.g. 'one {a2eb8a...781679b_pl_0} other {a2eb8a...781679b_pl_1}'
        return self.serialize_strings(
            hashes_by_rule,
            syntax_by_rule=icu_string.syntax_by_rule,
        )

    @staticmethod
    def _create_placeholders_by_rule(icu_string, target_plural_forms):
        """Get a dictionary that has the hash placeholder that corresponds to
        each plural rule of the target language.

        It works by finding the prefix of the hash string that is
        associated with the given ICUString object, and creates a dictionary
        of all hashes, one for each rule of the target language.

        :param ICUString icu_string: the string to use
        :param list target_plural_forms: a list of the plural rule numbers
            that the target language supports
        :return: a dictionary with all hashes, e.g.
            {
               1: 'a2eb8a66695435a29ee61d5df781679b_pl_0',
               5: 'a2eb8a66695435a29ee61d5df781679b_pl_1',
            }
        :rtype: dict
        """
        hash_str = icu_string.strings_by_rule[5]  # rule 5 always exists
        hash_str = hash_str[:-1]  # remove last char (the plural index)
        return {
            rule: hash_str + str(index)
            for index, rule in enumerate(target_plural_forms)
        }
