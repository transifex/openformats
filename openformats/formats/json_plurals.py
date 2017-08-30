# -*- coding: utf-8 -*-

from __future__ import absolute_import

import re
import pyparsing

from ..exceptions import ParseError
from ..handlers import Handler
from ..formats.json import JsonHandler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.json import DumbJson


class JsonPluralsHandler(JsonHandler):
    """
    Responsible for KEYVALUEJSON files that support plurals as per ICU's
    message format.

    Not the full spec of message format is supported. Particularly,
    the following features are *not* supported:
      - the `offset` feature
      - the explicit count rule, e.g. `=0`, `=1`
    """

    name = "KEYVALUEJSON_PLURALS"
    extension = "json"

    PLURAL_ARG = 'plural'
    PLURAL_KEYS_STR = ' '.join(Handler._RULES_ATOI.keys())

    def _extract(self, parsed, nest=None):
        if parsed.type == dict:
            for key, key_position, value, value_position in parsed:
                key = self._escape_key(key)
                if nest is not None:
                    key = u"{}.{}".format(nest, key)

                # 'key' should be unique
                if key in self.existing_keys:
                    # Need this for line number
                    self.transcriber.copy_until(key_position)
                    raise ParseError(u"Duplicate string key ('{}') in line {}".
                                     format(key, self.transcriber.line_number))
                self.existing_keys.add(key)

                if isinstance(value, (str, unicode)):
                    if not value.strip():
                        continue

                    # First attempt to parse this as a special node,
                    # e.g. a pluralized string.
                    # If it cannot be parsed that way (returns None),
                    # parse it like a regular string.
                    openstring = self._parse_special(
                        key, value, value_position
                    )
                    if not openstring:
                        openstring = self._get_regular_string(
                            key, value, value_position
                        )

                    self.stringset.append(openstring)

                elif isinstance(value, DumbJson):
                    self._extract(value, key)

                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass

        elif parsed.type == list:
            for index, (item, item_position) in enumerate(parsed):
                if nest is None:
                    key = u"..{}..".format(index)
                else:
                    key = u"{}..{}..".format(nest, index)
                if isinstance(item, (str, unicode)):
                    if not item.strip():
                        continue

                    openstring = self._parse_special(key, item, item_position)
                    if not openstring:
                        openstring = self._get_regular_string(
                            key, item, item_position
                        )

                    self.stringset.append(openstring)

                elif isinstance(item, DumbJson):
                    self._extract(item, key)
                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass
        else:
            raise ParseError("Invalid JSON")

    def _parse_special(self, key, value, value_position):
        """
        Parse a string that follows a subset of the the ICU message format
        and return an OpenString object.

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
        :return: an OpenString or None
        """
        matches = re.match(
            ur'{\s*([A-Za-z-_\d]+),\s*([A-Za-z_]+)\s*,\s*(.*)}\s*', value
        )
        if not matches:
            return None

        keyword, argument, serialized_strings = matches.groups()

        if argument == self.PLURAL_ARG:
            return self._parse_pluralized_string(
                key, keyword, value, value_position,
                serialized_strings
            )

        return None

    def _get_regular_string(self, key, value, value_position):
        """
        Return a new OpenString based on the given key and value
        and update the transcriber accordingly.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        openstring = OpenString(key, value, order=next(self._order))
        self.transcriber.copy_until(value_position)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(value))

        return openstring

    def _parse_pluralized_string(self, key, keyword, value, value_position,
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
            e.g. 'one { I ate {count} apple. } other { I ate {count} apples. }'
        :return: A pluralized OpenString instance or None
        """

        # Each item should be like '<proper_plurality_rule_str> {<content>}'
        # Nested braces ({}) inside <content> are allowed.
        valid_plural_item = (
            pyparsing.oneOf(self.PLURAL_KEYS_STR) +
            pyparsing.nestedExpr('{', '}')
        )

        # We need to make sure that the plural rules are valid.
        # Therefore, we also match any <alphanumeric> {<content>} string
        # and see if there are differences compared to the valid results
        # we got above.
        any_plural_item = (
            pyparsing.Word(pyparsing.alphanums) +
            pyparsing.nestedExpr('{', '}')
        )

        all_matches = pyparsing.originalTextFor(any_plural_item).searchString(
            serialized_strings
        )
        self._validate_plural_content_format(
            key, value, serialized_strings, all_matches
        )

        # Create a list of serialized plural items, e.g.:
        # ['one { I ate {count} apple. }']
        valid_matches = pyparsing.originalTextFor(valid_plural_item)\
            .searchString(serialized_strings)

        # Make sure the plurality rules are valid
        # If not, an error will be raised
        if len(valid_matches) != len(all_matches):
            self._handle_invalid_plural_format(
                serialized_strings, any_plural_item, key, value
            )

        # Create a list of tuples [(plurality_str, content_with_braces)]
        all_strings_list = [
            JsonPluralsHandler._parse_plural_content(match[0])
            for match in valid_matches
        ]

        # Convert it to a dict like { 'one': '{...}', 'other': '{...}' }
        # And then to a dict like { 1: '...', 5: '...' }
        all_strings_dict = dict(all_strings_list)
        all_strings_dict = {
            Handler.get_rule_number(plurality_str): content[1:-1]
            for plurality_str, content in all_strings_dict.iteritems()
        }

        openstring = OpenString(key, all_strings_dict, order=next(self._order))

        # ICU's message format contains an arbitrary string at the beginning.
        # We need to include that in the template, because otherwise we won't
        # have enough information to recreate it in the compilation phase.
        # e.g. in { item_count, plural, other {You have {file_count} files.} }
        # `item_count` is a string set by the user, it's not a standard.
        # We'll keep everything up to the comma that follows the 'plural'
        # argument.
        current_pos = value.index(keyword) + len(keyword)
        current_pos = value.index(self.PLURAL_ARG, current_pos)\
            + len(self.PLURAL_ARG)
        current_pos = value.index(',', current_pos) + len(',')

        # We want to preserve the original document as much as possible,
        # so we'll add any whitespace between the comma and the
        # first plurality rule, e.g. 'one'
        current_pos = value.index(all_strings_list[0][0], current_pos)

        # Also include whitespace between the last two closing braces
        second_last_closing_brace = value.rfind('}', 0, value.rfind('}')) + 1
        string_to_replace = value[current_pos:second_last_closing_brace]

        self.transcriber.copy_until(value_position + current_pos)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_to_replace))

        return openstring

    def _validate_plural_content_format(self, key, value, serialized_strings,
                                        all_matches):
        """
        Make sure the serialized content is properly formatted
        as one or more pluralized strings.
        :param key: the string key
        :param value: the whole value of the key, e.g.
            { item_count, plural, zero {...} one {...} other {...}}
        :param serialized_strings: the part of the value that holds the
            string information only, e.g.
            zero {...} one {...} other {...}
        :param all_matches: a pyparsing element that matches all strings
            formatted like '<alphanumeric> {...}'

        :raise: ParseError
        """
        remaining_str = serialized_strings
        for match in all_matches:
            remaining_str = remaining_str.replace(match[0], '')

        if len(remaining_str.strip()) > 0:
            raise ParseError(
                'Invalid format of pluralized entry '
                'with key: "{}", serialized translations: "{}". '
                'Could not parse the following chunk: "{}". '
                'There are some invalid braces ("{{", "}}") '
                'in the translations.'.format(
                    key, serialized_strings, remaining_str
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
            'Invalid plural rule(s): {} in pluralized entry '
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

    def compile(self, template, stringset, **kwargs):
        # Lets play on the template first, we need it to not include the hashes
        # that aren't in the stringset. For that we will create a new stringset
        # which will have the hashes themselves as strings and compile against
        # that. The compilation process will remove any string sections that
        # are absent from the stringset. Next we will call `_clean_empties`
        # from the template to clear out any `...,  ,...` or `...{ ,...`
        # sequences left. The result will be used as the actual template for
        # the compilation process

        stringset = list(stringset)

        fake_stringset = [
            OpenString(openstring.key,
                       openstring.template_replacement,
                       order=openstring.order,
                       pluralized=openstring.pluralized)
            for openstring in stringset
        ]
        new_template = self._replace_translations(
            template, fake_stringset, False
        )
        new_template = self._clean_empties(new_template)

        return self._replace_translations(new_template, stringset, True)

    def _replace_translations(self, template, stringset, is_real_stringset):
        self.transcriber = Transcriber(template)
        template = self.transcriber.source

        self.stringset = stringset
        self.stringset_index = 0

        parsed = DumbJson(template)
        self._insert(parsed, is_real_stringset)

        self.transcriber.copy_until(len(template))
        return self.transcriber.get_destination()

    def _insert(self, parsed, is_real_stringset):
        if parsed.type == dict:
            return self._insert_from_dict(parsed, is_real_stringset)
        elif parsed.type == list:
            return self._insert_from_list(parsed, is_real_stringset)

    def _insert_item(self, value, value_position, is_real_stringset):
        at_least_one = False

        if isinstance(value, (str, unicode)):
            string = self._get_next_string()
            string_exists = string is not None

            templ_replacement = string.template_replacement \
                if string_exists else None

            # Pluralized string
            if string_exists and string.pluralized \
                    and templ_replacement in value:
                at_least_one = True
                self._insert_plural_string(
                    value, value_position, string, is_real_stringset
                )

            # Regular string
            elif (string_exists and value == templ_replacement):
                at_least_one = True
                self._insert_regular_string(
                    value, value_position, string, is_real_stringset
                )

            # Anything else: just remove the current section
            else:
                self._copy_until_and_remove_section(
                    value_position + len(value) + 1
                )

        elif isinstance(value, DumbJson):
            items_still_left = self._insert(value, is_real_stringset)

            if not items_still_left:
                self._copy_until_and_remove_section(value.end + 1)
            else:
                at_least_one = True

        else:
            # 'value' is a python value allowed by JSON (integer,
            # boolean, null), skip it
            at_least_one = True

        return at_least_one

    def _insert_from_dict(self, parsed, is_real_stringset):
        at_least_one = False

        for key, key_position, value, value_position in parsed:

            self.transcriber.copy_until(key_position - 1)
            self.transcriber.mark_section_start()

            tmp_at_least_one = self._insert_item(
                value, value_position, is_real_stringset
            )

            if tmp_at_least_one:
                at_least_one = True

        return at_least_one

    def _insert_from_list(self, parsed, is_real_stringset):
        at_least_one = False

        for value, value_position in parsed:
            self.transcriber.copy_until(value_position - 1)
            self.transcriber.mark_section_start()

            tmp_at_least_one = self._insert_item(
                value, value_position, is_real_stringset
            )

            if tmp_at_least_one:
                at_least_one = True

        return at_least_one

    def _insert_plural_string(self, value, value_position, string,
                              is_real_stringset):
        templ_replacement = string.template_replacement
        replacement_pos = value.find(templ_replacement)

        if is_real_stringset:
            replacement = \
                JsonPluralsHandler.serialize_pluralized_string(
                    string, delimiter=' '
                )
        else:
            replacement = templ_replacement

        self.transcriber.copy_until(
            value_position + replacement_pos
        )
        self.transcriber.add(replacement)

        self.transcriber.skip(len(templ_replacement))
        self.transcriber.copy(
            len(value) - replacement_pos - len(templ_replacement)
        )
        self.stringset_index += 1

    def _insert_regular_string(self, value, value_position, string,
                               is_real_stringset):
        self.transcriber.copy_until(value_position)
        self.transcriber.add(string.string)
        self.transcriber.skip(len(value))
        self.stringset_index += 1

    def _copy_until_and_remove_section(self, pos):
        """
        Copy characters to the transcriber until the given position,
        then end the current section and remove it altogether.
        """
        self.transcriber.copy_until(pos)
        self.transcriber.mark_section_end()
        self.transcriber.remove_section()

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
