# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import re
from itertools import count
import copy

import six

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.icu import ICUCompiler, ICUParser
from ..utils.json import DumbJson


class JsonHandler(Handler):
    """
    Responsible for KEYVALUEJSON files that support plurals as per ICU's
    message format.

    Not the full spec of message format is supported. Particularly,
    the following features are *not* supported:
      - the `offset` feature
      - the explicit count rule, e.g. `=0`, `=1`
    """

    name = "KEYVALUEJSON"
    extension = "json"

    PLURAL_ARG = 'plural'
    PLURAL_KEYS_STR = ' '.join(six.iterkeys(Handler._RULES_ATOI))

    def parse(self, content, **kwargs):
        # Validate that content is JSON
        self.validate_content(content)

        self.transcriber = Transcriber(content)
        source = self.transcriber.source
        self.stringset = []
        self.existing_keys = set()

        try:
            parsed = DumbJson(source)
        except ValueError as e:
            raise ParseError(six.text_type(e))
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

                if isinstance(value, (six.binary_type, six.text_type)):
                    if not value.strip():
                        continue

                    openstring = self._create_openstring(key, value,
                                                         value_position)
                    if openstring:
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
                if isinstance(item, (six.binary_type, six.text_type)):
                    if not item.strip():
                        continue

                    openstring = self._create_openstring(key, item,
                                                         item_position)
                    if openstring:
                        self.stringset.append(openstring)

                elif isinstance(item, DumbJson):
                    self._extract(item, key)
                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass
        else:
            raise ParseError("Invalid JSON")

    def _create_openstring(self, key, value, value_position):
        """Return a new OpenString based on the given key and value
        and update the transcriber accordingly based on the provided position.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        # First attempt to parse this as a special node,
        # e.g. a pluralized string.
        # If it cannot be parsed that way (returns None), parse it like
        # a regular string.
        parser = ICUParser(allow_numeric_plural_values=False)
        icu_string = parser.parse(key, value)
        if icu_string:
            return self._create_pluralized_string(icu_string, value_position)

        return self._create_regular_string(
            key, value, value_position
        )

    def _create_pluralized_string(self, icu_string, value_position):
        """Create a pluralized string based on the given information.

        Also updates the transcriber accordingly.

        :param ICUString icu_string:
        :return: an OpenString object
        :rtype: OpenString
        """
        openstring = OpenString(
            icu_string.key,
            icu_string.strings_by_rule,
            pluralized=icu_string.pluralized,
            order=next(self._order),
        )

        current_pos = icu_string.current_position
        string_to_replace = icu_string.string_to_replace

        self.transcriber.copy_until(value_position + current_pos)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_to_replace))

        return openstring

    def _create_regular_string(self, key, value, value_position):
        """Return a new simple OpenString based on the given key and value
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

        if isinstance(value, (six.binary_type, six.text_type)):
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
            elif string_exists and value == templ_replacement:
                at_least_one = True
                self._insert_regular_string(
                    value, value_position, string, is_real_stringset
                )

            else:
                # Anything else: just remove the current section
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
            replacement = ICUCompiler().serialize_strings(string.string,
                                                          delimiter=' ')
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

    def validate_content(self, content):
        """Validate that a given string is valid JSON format.

        :param str content: the content to parse
        :raise ParseError: if the content is not valid JSON format
        """
        try:
            json.loads(content)
        except ValueError as e:
            raise ParseError(six.text_type(e))

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
                    unescaped = unicode_escaped.\
                        encode('ascii').\
                        decode('unicode-escape')
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


class StructuredJsonHandler(JsonHandler):
    """Handler that preserves certain keys for internal usage, while
    keeping the flexibility and functionality of the original JsonHandler. It
    should be used in cases where developers want to add certain metadata
    to their source entities, like developer_comments or context. The parent
    handler would parse them as valid key-value entries, however this new
    one will use them to enhance the OpenString object.

    Currently, we reserve the following keywords:
    - string
    - context
    - developer_comment
    - character_limit

    Naturally, all of these originate from the OpenString class, but future
    reserved keywords don't have to be limited to that.

    Example:
    {
      "key": {
        "string": "{count, plural, one {{cnt} file.} other {{cnt} files.}}",
        "developer_comment": "This is a developer comment",
        "context": "Sentence",
        "character_limit": 100
        }
    }
    Because the format assumes that each string when parsed will contain a
    dictionary with at least one element in it (ex. "string"),
    StructuredJsonHandler does not support lists, something that the parent
    parser does.

    As an example, ["a string", "another string"] will not be parsed and will
    instead be part of the actual template
    """

    name = "STRUCTURED_JSON"

    STRING_KEY = "string"
    CONTEXT_KEY = "context"
    DEVELOPER_COMMENT_KEY = "developer_comment"
    CHARACTER_LIMIT_KEY = "character_limit"
    STRUCTURE_FIELDS = {CONTEXT_KEY, DEVELOPER_COMMENT_KEY,
                        CHARACTER_LIMIT_KEY}

    def _create_pluralized_string(self, icu_string, value_position):
        """Create a pluralized string based on the given information.

        Also updates the transcriber accordingly.

        :param ICUString icu_string: The ICUString object that will generate
            the pluralized string
        :return: an OpenString object
        :rtype: OpenString
        """
        icu_string.key = self._parse_key(icu_string.key)
        # Don't create strings for metadata fields
        if not icu_string.key:
            return None

        structure = self._get_string_structure(icu_string.key)
        openstring = OpenString(
            icu_string.key,
            icu_string.strings_by_rule,
            pluralized=icu_string.pluralized,
            order=next(self._order),
            developer_comment=structure[self.DEVELOPER_COMMENT_KEY],
            character_limit=structure[self.CHARACTER_LIMIT_KEY],
            context=structure[self.CONTEXT_KEY]
        )

        current_pos = icu_string.current_position
        string_to_replace = icu_string.string_to_replace

        self.transcriber.copy_until(value_position + current_pos)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_to_replace))

        return openstring

    def _create_regular_string(self, key, value, value_position):
        """
        Return a new OpenString based on the given key and value
        and update the transcriber accordingly.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        key = self._parse_key(key)
        # Don't create strings for metadata fields
        if not key:
            return None

        structure = self._get_string_structure(key)
        openstring = OpenString(
            key, value, order=next(self._order),
            developer_comment=structure[self.DEVELOPER_COMMENT_KEY],
            character_limit=structure[self.CHARACTER_LIMIT_KEY],
            context=structure[self.CONTEXT_KEY]
        )
        self.transcriber.copy_until(value_position)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(value))

        return openstring

    def _parse_key(self, key):
        """Return the proper key for translatable entries or None
        for metadata entries or other keys that don't match those cases.

        Examples:
        - The key "first.second.string" ends in '.string' and thus
          it points to a translatable string. The method will return
          'first.second' as the final key
        - The key "first.second.context" points to a metadata value
          ('context'), so the method will return None

        :param str key: The key to check against
        :return: The updated key if this is a valid key, None otherwise
        :rtype: str
        """
        # We need to parse only STRING_KEY keys, otherwise we should
        # early return
        if not key.endswith(".{}".format(self.STRING_KEY)):
            return None
        # Remove the STRING_KEY part of the key as it is not needed. Add +1
        # when calculating the length of the STRING_KEY, for the "." character
        return key[:-(len(self.STRING_KEY)+1)]

    def _get_string_structure(self, key):
        """Given a key, find its corresponding value in a nested JSON object.

        Example:
        If our JSON file has the following structure,
        {'key':{
            'another_key':{
                'string': 'This is a text',
                'developer_comment': 'These are the developer notes'
            }
          }
        }
        Then given the key `key.another_key`, the _get_string_structure
        function will return the following dictionary:
        {
            "string": "This is a text",
            "context": "",
            "developer_comment": "These are the developer notes",
            "character_limit": None
        }

        :param str key: the key to search against
        :return: a dictionary with the string structure
        :rtype: dict
        """
        json_dict = self._get_value_for_key(key)
        return {field: json_dict[field]
                if field in json_dict
                else OpenString.DEFAULTS[field]
                for field in self.STRUCTURE_FIELDS
                }

    def _get_value_for_key(self, key):
        """Given a key, find its value in a nested JSON object.

        Key will always have the format `key.[another_key[..]]`
        As an example, given the key 'key.another_key.string'
        and our JSON object has the following structure:
        {'key':{
            'another_key':{
                'string': 'This is a text',
                'developer_comment': 'These are the developer notes'
            }
          }
        }
        We should return the following dictionary:
        {
            'string': 'This is a text',
            'developer_comment': 'These are the developer notes'
        }

        :param str key: the key to search against
        :return: a dictionary with the value for the given key
        :rtype: dict
        """
        # Go through all parts of the composite key
        keys = key.split('.')
        json_dict = self.json_dict
        for k in keys:
            json_dict = json_dict[k]
        return json_dict

    def validate_content(self, content):
        """Validate that a given string is valid JSON file.

        :param str content: the content to parse
        :raise ParseError: if the content is not valid JSON format
        """
        try:
            # Save the JSON dict for later use
            self.json_dict = json.loads(content)
        except ValueError as e:
            raise ParseError(six.text_type(e))

    def _copy_until_and_remove_section(self, pos):
        """
        Copy characters to the transcriber until the given position,
        then end the current section.
        """
        self.transcriber.copy_until(pos)
        self.transcriber.mark_section_end()
        # Unlike the JSON format, do not remove the remaining section of the
        # template


class ChromeI18nHandler(JsonHandler):
    """Responsible for CHROME files, based on the JsonHandler."""

    name = "CHROME"
    STRING_KEY = "message"

    def compile(self, template, stringset, **kwargs):
        """Compile a template back to a stringset.

        :param str template: the template string
        :param stringset: generator that holds a list of OpenString objects
        :return: the compiled template
        :rtype: str
        """
        stringset = list(stringset)
        return self._replace_translations(
            template, stringset, is_real_stringset=True
        )

    def _create_regular_string(self, key, value, value_position):
        """
        Return a new OpenString based on the given key and value
        and update the transcriber accordingly.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        # We should only parse keys with a specific value ("message"). All
        # others should be added in the template
        # Key's format is parent_name.key_name (ex. test.message,
        # test.description etc)
        if not key.endswith(self.STRING_KEY):
            return None
        # Check if the given key has a description field
        description = self._get_description(key)
        # Create an OpenString object with the description as the developer
        # comment
        openstring = OpenString(
            key, value, order=next(self._order), developer_comment=description
        )
        self.transcriber.copy_until(value_position)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(value))

        return openstring

    def _get_description(self, key):
        """Return the 'description' child for a given key

        :param str key: the key to search against
        :return: the description string
        :rtype: str
        """
        key_split = key.split('.')
        try:
            return self.json_dict[key_split[0]]['description']
        except KeyError:
            return ''

    def _copy_until_and_remove_section(self, pos):
        """
        Copy characters to the transcriber until the given position,
        then end the current section.
        """
        self.transcriber.copy_until(pos)
        self.transcriber.mark_section_end()
        # Unlike the JSON format, do not remove the remaining section of the
        # template

    def validate_content(self, content):
        """Validate that a given string is valid Chromei18n file.

        :param str content: the content to parse
        :raise ParseError: if the content is not valid JSON format
        """
        try:
            # Save the JSON dict for later use
            self.json_dict = json.loads(content)
        except ValueError as e:
            raise ParseError(six.text_type(e))
