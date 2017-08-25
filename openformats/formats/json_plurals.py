# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import re
from itertools import count
import pyparsing

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.json import DumbJson


class JsonPluralsHandler(Handler):

    name = "KEYVALUEJSON_PLURALS"
    extension = "json"

    MESSAGE_FORMAT_STRUCTURE = re.compile(
        ur'{\s*([A-Za-z-_\d]+),\s*([A-Za-z_]+)\s*,\s*(.*)}'
    )
    PLURAL_ARG = 'plural'
    PLURAL_KEYS_STR = ' '.join(Handler._RULES_ATOI.keys())

    def parse(self, content, **kwargs):
        # Do a first pass using the `json` module to ensure content is valid
        try:
            json.loads(content)
        except ValueError, e:
            raise ParseError(e.message)

        self.transcriber = Transcriber(content)
        source = self.transcriber.source
        self.stringset = []
        self.existing_keys = set()

        try:
            parsed = DumbJson(source)
        except ValueError, e:
            raise ParseError(e.message)
        self._order = count()
        self._extract(parsed)
        self.transcriber.copy_until(len(source))

        return self.transcriber.get_destination(), self.stringset

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

                    openstring = self._parse_special(
                        key, key_position, value, value_position
                    )

                    if openstring:
                        self.stringset.append(openstring)

                    else:
                        openstring = OpenString(key, value,
                                                order=next(self._order))
                        self.transcriber.copy_until(value_position)
                        self.transcriber.add(openstring.template_replacement)
                        self.transcriber.skip(len(value))
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
                    openstring = OpenString(key, item, order=next(self._order))
                    self.transcriber.copy_until(item_position)
                    self.transcriber.add(openstring.template_replacement)
                    self.transcriber.skip(len(item))
                    self.stringset.append(openstring)
                elif isinstance(item, DumbJson):
                    self._extract(item, key)
                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass
        else:
            raise ParseError("Invalid JSON")

    def _parse_special(self, key, key_position, value, value_position):
        """
        Parse a string that follows a subset of the the ICU message format
        and return a list of OpenString objects.

        For the time being, only the plurals format is supported.
        If `value` doesn't match the proper format, it will return None.

        Note: if we want to support more ICU features in the future,
        this would probably have to be refactored.

        :param key: the string key
        :param value: the serialized string that has all the content,
            formatted like this (whitespace irrelevant):
            { item_count, plural,
                one { You have {file_count} file. }
                other { You have {file_count} files. }
            }
        :return: a list of OpenString elements or None
        """
        matches = self.MESSAGE_FORMAT_STRUCTURE.match(value)
        if not matches:
            return None

        keyword, argument, serialized_strings = matches.groups()

        if argument == self.PLURAL_ARG:
            return self._parse_pluralized_string(
                key, key_position, keyword, value, value_position,
                serialized_strings
            )

        return None

    def _parse_pluralized_string(self, key, key_position, keyword,
                                 value, value_position, serialized_strings):
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
        # Each item should be like '<plurality_rule_str> { <content> }'
        # Nested braces ({}) inside <content> are allowed.
        plural_item = (
            pyparsing.oneOf(self.PLURAL_KEYS_STR) +
            pyparsing.nestedExpr('{', '}')
        )

        # Create a list of serialized plural items, e.g.:
        # ['one { I ate {count} apple. }']
        matches = pyparsing.originalTextFor(
            plural_item
        ).searchString(
            serialized_strings
        )

        # Create a list of tuples [(plurality_str, content_with_braces)]
        all_strings_list = [
            JsonPluralsHandler._parse_plural_content(match[0])
            for match in matches
        ]

        # Convert it to a dict like { 'one': '{...}', 'other': '{...}' }
        # And then to a dict like { 1: '...', 5: '...' }
        all_strings_dict = dict(all_strings_list)
        all_strings_dict = {
            Handler.get_rule_number(plurality_str): content[1:-1]
            for plurality_str, content in all_strings_dict.iteritems()
        }

        openstring = OpenString(key, all_strings_dict, order=next(self._order))

        # ICU's message format contains an arbitrary string in the beginning.
        # We need to include that in the template, because otherwise we won't
        # have enough information to recreate it in the compilation phase.
        # e.g. in { item_count, plural, other {You have {file_count} files.} }
        # `item_count` is a string set by the user, it's not a standard.
        # We'll keep everything up to the comma that follows the 'plural'
        # argument.
        current_pos = value.index(keyword) + len(keyword)
        current_pos = value.index(self.PLURAL_ARG, current_pos) \
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

    @staticmethod
    def _parse_plural_content(string):
        # Find the content inside the brackets
        opening_brace_index = string.index('{')
        content = string[opening_brace_index:]

        # Find the plurality type (zero, one, etc)
        plurality = string[:opening_brace_index].strip()

        return plurality, content

    @staticmethod
    def _escape_key(key):
        key = key.replace(DumbJson.BACKSLASH,
                          u''.join([DumbJson.BACKSLASH, DumbJson.BACKSLASH]))
        key = key.replace(u".", u''.join([DumbJson.BACKSLASH, '.']))
        return key

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
        new_template = self._replace_translations(template, fake_stringset, False)
        new_template = self._clean_empties(new_template)

        return self._replace_translations(new_template, stringset, True)

    def _replace_translations(self, template, stringset, is_real_stringset):
        self.transcriber = Transcriber(template)
        template = self.transcriber.source
        self.stringset = stringset
        self.stringset_index = 0
        parsed = DumbJson(template)
        self._intract(parsed, is_real_stringset)

        self.transcriber.copy_until(len(template))
        return self.transcriber.get_destination()

    def _intract(self, parsed, is_real_stringset):
        if parsed.type == dict:
            return self._intract_dict(parsed, is_real_stringset)
        elif parsed.type == list:
            return self._intract_list(parsed, is_real_stringset)

    def _intract_dict(self, parsed, is_real_stringset):
        at_least_one = False
        for key, key_position, value, value_position in parsed:

            self.transcriber.copy_until(key_position - 1)
            self.transcriber.mark_section_start()

            if isinstance(value, (str, unicode)):
                string = self._get_next_string()

                string_exists = string is not None
                templ_replacement = string.template_replacement

                if string_exists and string.pluralized \
                        and templ_replacement in value:
                    at_least_one = True
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

                elif (string_exists and value == templ_replacement):
                    at_least_one = True
                    self.transcriber.copy_until(value_position)
                    self.transcriber.add(string.string)
                    self.transcriber.skip(len(value))
                    self.stringset_index += 1
                else:
                    self.transcriber.copy_until(value_position +
                                                len(value) + 1)
                    self.transcriber.mark_section_end()
                    self.transcriber.remove_section()

            elif isinstance(value, DumbJson):
                all_removed = self._intract(value, is_real_stringset)

                if all_removed:
                    self.transcriber.copy_until(value.end + 1)
                    self.transcriber.mark_section_end()
                    self.transcriber.remove_section()
                else:
                    at_least_one = True

            else:
                # 'value' is a python value allowed by JSON (integer,
                # boolean, null), skip it
                at_least_one = True

        return not at_least_one

    def _intract_list(self, parsed, is_real_stringset):
        at_least_one = False
        for item, item_position in parsed:
            self.transcriber.copy_until(item_position - 1)
            self.transcriber.mark_section_start()
            if isinstance(item, (str, unicode)):
                string = self._get_next_string()
                if (string is not None and
                        item == string.template_replacement):
                    at_least_one = True
                    self.transcriber.copy_until(item_position)
                    self.transcriber.add(string.string)
                    self.transcriber.skip(len(item))
                    self.stringset_index += 1
                else:
                    self.transcriber.copy_until(item_position + len(item) + 1)
                    self.transcriber.mark_section_end()
                    self.transcriber.remove_section()
            elif isinstance(item, DumbJson):
                all_removed = self._intract(item, is_real_stringset)
                if all_removed:
                    self.transcriber.copy_until(item.end + 1)
                    self.transcriber.mark_section_end()
                    self.transcriber.remove_section()
                else:
                    at_least_one = True
            else:
                # 'value' is a python value allowed by JSON (integer,
                # boolean, null), skip it
                at_least_one = True
        return not at_least_one

    def _clean_empties(self, compiled):
        """ If sections were removed, clean leftover commas, brackets etc.

            Eg:
                '{"a": "b", ,"c": "d"}' -> '{"a": "b", "c": "d"}'
                '{, "a": "b", "c": "d"}' -> '{"a": "b", "c": "d"}'
                '["a", , "b"]' -> '["a", "b"]'
        """
        while True:
            # First key-value of a dict was removed
            match = re.search(r'{\s*,', compiled)
            if match:
                compiled = u"{}{{{}".format(compiled[:match.start()],
                                            compiled[match.end():])
                continue

            # Last key-value of a dict was removed
            match = re.search(r',\s*}', compiled)
            if match:
                compiled = u"{}}}{}".format(compiled[:match.start()],
                                            compiled[match.end():])
                continue

            # First item of a list was removed
            match = re.search(r'\[\s*,', compiled)
            if match:
                compiled = u"{}[{}".format(compiled[:match.start()],
                                           compiled[match.end():])
                continue

            # Last item of a list was removed
            match = re.search(r',\s*\]', compiled)
            if match:
                compiled = u"{}]{}".format(compiled[:match.start()],
                                           compiled[match.end():])
                continue

            # Intermediate key-value of a dict or list was removed
            match = re.search(r',\s*,', compiled)
            if match:
                compiled = u"{},{}".format(compiled[:match.start()],
                                           compiled[match.end():])
                continue

            # No substitutions happened, break
            break

        return compiled

    def _get_next_string(self):
        try:
            return self.stringset[self.stringset_index]
        except IndexError:
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
            '{} {{{}}}'.format(
                Handler.get_rule_string(rule),
                translation
            )
            for rule, translation in pluralized_string.string.iteritems()
        ]
        return delimiter.join(plural_list)

    @classmethod
    def escape(cls, string):
        return u''.join(cls._escape_generator(string))
        # btw, this seems equivalent to
        # return json.dumps(string, ensure_ascii=False)[1:-1]

    @staticmethod
    def _escape_generator(string):
        for symbol in string:
            if symbol == DumbJson.DOUBLE_QUOTES:
                yield DumbJson.BACKSLASH
                yield DumbJson.DOUBLE_QUOTES
            elif symbol == DumbJson.BACKSLASH:
                yield DumbJson.BACKSLASH
                yield DumbJson.BACKSLASH
            elif symbol == DumbJson.BACKSPACE:
                yield DumbJson.BACKSLASH
                yield u'b'
            elif symbol == DumbJson.FORMFEED:
                yield DumbJson.BACKSLASH
                yield u'f'
            elif symbol == DumbJson.NEWLINE:
                yield DumbJson.BACKSLASH
                yield u'n'
            elif symbol == DumbJson.CARRIAGE_RETURN:
                yield DumbJson.BACKSLASH
                yield u'r'
            elif symbol == DumbJson.TAB:
                yield DumbJson.BACKSLASH
                yield u't'
            else:
                yield symbol

    @classmethod
    def unescape(cls, string):
        return u''.join(cls._unescape_generator(string))
        # btw, this seems equivalent to
        # return json.loads(u'"{}"'.format(string))

    @staticmethod
    def _unescape_generator(string):
        # I don't like this aldschool approach, but we may have to rewind a bit
        ptr = 0
        while True:
            if ptr >= len(string):
                break

            symbol = string[ptr]

            if symbol != DumbJson.BACKSLASH:
                yield symbol
                ptr += 1
                continue

            try:
                next_symbol = string[ptr + 1]
            except IndexError:
                yield DumbJson.BACKSLASH
                ptr += 1
                continue

            if next_symbol in (DumbJson.DOUBLE_QUOTES, DumbJson.FORWARD_SLASH,
                               DumbJson.BACKSLASH):
                yield next_symbol
                ptr += 2
            elif next_symbol == u'b':
                yield DumbJson.BACKSPACE
                ptr += 2
            elif next_symbol == u'f':
                yield DumbJson.FORMFEED
                ptr += 2
            elif next_symbol == u'n':
                yield DumbJson.NEWLINE
                ptr += 2
            elif next_symbol == u'r':
                yield DumbJson.CARRIAGE_RETURN
                ptr += 2
            elif next_symbol == u't':
                yield DumbJson.TAB
                ptr += 2
            elif next_symbol == u'u':
                unicode_escaped = string[ptr:ptr + 6]
                try:
                    unescaped = unicode_escaped.decode('unicode-escape')
                except Exception:
                    yield DumbJson.BACKSLASH
                    yield u'u'
                    ptr += 2
                    continue
                if len(unescaped) != 1:
                    yield DumbJson.BACKSLASH
                    yield u'u'
                    ptr += 2
                    continue
                yield unescaped
                ptr += 6

            else:
                yield symbol
                ptr += 1