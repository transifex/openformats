# -*- coding: utf-8 -*-

from __future__ import absolute_import

import csv
import json
import re
from itertools import count

import six

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.icu import ICUCompiler, ICUParser
from ..utils.json import DumbJson, escape, unescape

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def csv_reader_next(reader):
    try:
        return reader.next()
    except AttributeError:
        return next(reader)


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

                if self.name == "STRUCTURED_JSON":
                    try:
                        (string_value, _), = value.find_children(self.STRING_KEY)
                    except:
                        # Ignore other types of values like lists
                        pass
                    else:
                        if string_value:
                            if isinstance(string_value, (six.binary_type,
                                                         six.text_type)):
                                if string_value.strip():
                                    openstring = self._create_openstring(
                                        key, value)

                                    if openstring:
                                        self.stringset.append(openstring)

                        elif isinstance(value, DumbJson):
                            self._extract(value, key)
                else:
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
            if value != '':
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
                        value, value_position, string.string
                    )

                else:
                    # Anything else: just remove the current section
                    self._copy_until_and_remove_section(
                        value_position + len(value) + 1
                    )
            else:
                # value is an empty string, add the key but don't update stringset_index
                at_least_one = True
                self._insert_regular_string(
                    value, value_position, '', False
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
        at_least_one = not bool(list(parsed))

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
        at_least_one = not bool(list(parsed))

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
                               update_stringset_index=True):
        self.transcriber.copy_until(value_position)
        self.transcriber.add(string)
        self.transcriber.skip(len(value))
        if update_stringset_index:
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

    @staticmethod
    def escape(string):
        return escape(string)

    @staticmethod
    def unescape(string):
        return unescape(string)


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

    def compile(self, template, translations, **kwargs):
        self.translations = iter(translations)
        self.transcriber = Transcriber(template)
        template = self.transcriber.source

        dumb_template = DumbJson(template)
        self._compile_recursively(dumb_template)
        self.transcriber.copy_to_end()
        return self.transcriber.get_destination()

    def _compile_value(self, value, template_value, value_position):
        if value is not None:
            self.transcriber.add(u"{}".format(value))
        else:
            self.transcriber.add(u"null")
        self.transcriber.skip(len(u"{}".format(template_value)))
        self.transcriber.copy_until(value_position + len(u"{}".format(template_value)) + 1)

    def _compile_recursively(self, current_part):
        if isinstance(current_part, DumbJson):
            if current_part.type == list:
                for value, value_position in current_part:
                    self._compile_recursively(value)
            if current_part.type == dict:
                (value, _) = current_part.find_children(self.STRING_KEY)[0]
                if not value:
                    for key, key_position, value, value_position in current_part:
                        self.transcriber.copy_until(key_position - 1)
                        self.transcriber.copy_until(value_position)
                        self._compile_recursively(value)
                else:
                    translation = next(self.translations, None)
                    context_added = False
                    character_limit_added = False
                    developer_comments_added = False

                    line_separator = None
                    key_value_separator = None
                    for key, key_position, value, value_position in current_part:
                        prev_position_end = self.transcriber.ptr
                        line_separator = current_part.source[prev_position_end+1:key_position-1]
                        key_value_separator = current_part.source[key_position+len(key):value_position-1]
                        self.transcriber.copy_until(key_position - 1)
                        self.transcriber.copy_until(value_position)
                        if key == self.CONTEXT_KEY and translation:
                            context = translation.context
                            self._compile_value(self.escape(context), value, value_position)
                            context_added = True
                        elif key == self.DEVELOPER_COMMENT_KEY and translation:
                            developer_comment = translation.developer_comment
                            self._compile_value(self.escape(developer_comment), value, value_position)
                            developer_comments_added = True
                        elif key == self.CHARACTER_LIMIT_KEY and translation:
                            character_limit = translation.character_limit
                            self._compile_value(character_limit, value, value_position)
                            character_limit_added = True
                        elif key == self.STRING_KEY and translation:
                            if translation.pluralized:
                                string_replacement = ICUCompiler().serialize_strings(translation.string, delimiter=' ')
                                string_replacement = value.replace(translation.template_replacement, string_replacement)
                            else:
                                string_replacement = translation.string
                            self._compile_value(string_replacement, value, value_position)
                        elif not isinstance(value, DumbJson):
                            self.transcriber.copy_until(value_position + len(u"{}".format(value)) + 1)

                    extra_elements = []
                    if not context_added and translation and translation.context:
                        extra_elements.append(u"\"{}{}\"{}\"".format(
                            "context", key_value_separator, self.escape(translation.context)))
                    if not character_limit_added and translation and translation.character_limit:
                        extra_elements.append(u"\"{}{}{}".format(
                            "character_limit", key_value_separator, translation.character_limit))
                    if not developer_comments_added and translation and translation.developer_comment:
                        extra_elements.append(u"\"{}{}\"{}\"".format(
                            "developer_comment", key_value_separator, self.escape(translation.developer_comment)))
                    if extra_elements:
                        self.transcriber.add("," + line_separator + ("," + line_separator).join(extra_elements))

    def _create_openstring(self, key, payload_dict):
        """Return a new OpenString based on the given key and payload_dict
        and update the transcriber accordingly based on the provided position.


        :param str key: the string key
        :param DumbJson payload_dict: the string and metadata
        :return: an OpenString or None
        """
        # First attempt to parse this as a special node,
        # e.g. a pluralized string.
        # If it cannot be parsed that way (returns None), parse it like
        # a regular string.
        parser = ICUParser(allow_numeric_plural_values=False)
        (string_value, _), = payload_dict.find_children(self.STRING_KEY)
        icu_string = parser.parse(key, string_value)
        if icu_string:
            return self._create_pluralized_string(icu_string, payload_dict)

        return self._create_regular_string(
            key, payload_dict
        )

    def _create_pluralized_string(self, icu_string, payload_dict):
        """Create a pluralized string based on the given information.

        Also updates the transcriber accordingly.

        :param ICUString icu_string: The ICUString object that will generate
            the pluralized string
        "param DumbJson payload_dict: the string and metadata
        :return: an OpenString object
        :rtype: OpenString
        """
        (_, string_position), = payload_dict.find_children(self.STRING_KEY)
        payload_dict = json.loads(
            payload_dict.source[payload_dict.start:payload_dict.end+1])
        comment_value = payload_dict.get(self.DEVELOPER_COMMENT_KEY)
        limit_value = payload_dict.get(self.CHARACTER_LIMIT_KEY)
        context_value = payload_dict.get(self.CONTEXT_KEY)

        openstring = OpenString(
            icu_string.key,
            icu_string.strings_by_rule,
            pluralized=icu_string.pluralized,
            order=next(self._order),
            developer_comment=comment_value or '',
            character_limit=limit_value,
            context=context_value or ''
        )

        current_pos = icu_string.current_position
        string_to_replace = icu_string.string_to_replace

        self.transcriber.copy_until(string_position + current_pos)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_to_replace))

        return openstring

    def _create_regular_string(self, key, payload_dict):
        """
        Return a new OpenString based on the given key and value
        and update the transcriber accordingly.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        (string_value, string_position), = payload_dict.find_children(self.STRING_KEY)
        payload_dict = json.loads(
            payload_dict.source[payload_dict.start:payload_dict.end+1])
        comment_value = payload_dict.get(self.DEVELOPER_COMMENT_KEY)
        limit_value = payload_dict.get(self.CHARACTER_LIMIT_KEY)
        context_value = payload_dict.get(self.CONTEXT_KEY)

        openstring = OpenString(
            key, string_value, order=next(self._order),
            developer_comment=comment_value or '',
            character_limit=limit_value,
            context=context_value or ''
        )
        self.transcriber.copy_until(string_position)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_value))

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
        keys = csv_reader_next(
            csv.reader(
                StringIO(key), delimiter='.', escapechar="\\"
            )
        )
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


class ChromeI18nHandlerV3(Handler):
    """ New version of chrome-json handler.

        Compared to v2, this handler:
        - Only accepts a flat JSON structure, ie all strings must be at the top
          level of the root object
        - Does not escape keys; the same key that appears in the source file
          will be the key of the extracted string
        - Fixes a bug with parsing descriptions/comments; the previous version
          would not detect the description if the key had a dot (`.`) in it

        Example source file:

            {
                "a": {"message": "aaa"},
                "b": {"message": "bbb", "description": "description"},
                "c": {"message": "{plural, cnt, one {horse} other {horses}}"}
            }

        Extracted strings:

            |-----+-----------------------+-------------------|
            | key | string(s)             | developer_comment |
            |-----+-----------------------+-------------------|
            | a   | aaa                   |                   |
            | b   | bbb                   | description       |
            | c   | {1: horse, 5: horses} |                   |
            |-----+-----------------------+-------------------|
    """
    name = "CHROME_V3"
    extension = "json"

    def parse(self, content, **kwargs):
        icu_parser = ICUParser(allow_numeric_plural_values=False)

        # Sanity checks
        try:
            json.loads(content)
        except ValueError as e:
            raise ParseError(six.text_type(e))

        # Useful objects
        transcriber = Transcriber(content)
        source = transcriber.source
        stringset = []
        existing_keys = set()
        _order = count()

        # Sanity checks vol2
        try:
            parsed = DumbJson(source)
        except ValueError as e:
            raise ParseError(six.text_type(e))
        if parsed.type != dict:
            raise ParseError(u"Source file must be a JSON object")

        # Main loop
        for (outer_key,
             outer_key_position, outer_value, outer_value_position) in parsed:
            if outer_key in existing_keys:
                transcriber.copy_until(outer_key_position)
                raise ParseError(u"Key '{}' appears multiple times (line {})".
                                 format(outer_key, transcriber.line_number))
            existing_keys.add(outer_key)

            if not isinstance(outer_value, DumbJson):
                continue
            if outer_value.type != dict:
                continue

            # Figure out message and description
            (message, message_position), (description, _) = outer_value.\
                find_children('message', 'description')
            if not isinstance(message, six.string_types):
                continue
            if not isinstance(description, six.string_types):
                description = None

            # Extract string
            icu_string = icu_parser.parse(outer_key, message)
            if icu_string:
                # Pluralized
                openstring = OpenString(icu_string.key,
                                        icu_string.strings_by_rule,
                                        pluralized=icu_string.pluralized,
                                        order=next(_order),
                                        developer_comment=description or '')
                # Preserve ICU formatting:
                #   '{cnt, plural, one {foo} other {foos}}' ->
                #   '{cnt, plural, <hash>}'
                transcriber.copy_until(message_position +
                                       icu_string.current_position)
                transcriber.add(openstring.template_replacement)
                transcriber.skip(len(icu_string.string_to_replace))
            else:
                # Singular
                openstring = OpenString(outer_key, message,
                                        order=next(_order),
                                        developer_comment=description or '')
                transcriber.copy_until(message_position)
                transcriber.add(openstring.template_replacement)
                transcriber.skip(len(message))
            stringset.append(openstring)
        transcriber.copy_to_end()
        return transcriber.get_destination(), stringset

    def compile(self, template, stringset, **kwargs):
        icu_compiler = ICUCompiler()

        # Useful objects
        transcriber = Transcriber(template)
        source = transcriber.source
        stringset_iter = iter(stringset)
        openstring = next(stringset_iter, None)
        parsed = DumbJson(source)

        # Main loop
        for (outer_key,
             outer_key_position, outer_value, outer_value_position) in parsed:
            # Mark section start in case we want to delete this section
            transcriber.copy_until(outer_key_position - 1)
            transcriber.mark_section_start()

            # Not something we extracted a string from, skip
            if not isinstance(outer_value, DumbJson):
                continue
            if outer_value.type != dict:
                continue

            # Find message
            (message_hash, message_position), = outer_value.\
                find_children('message')

            # Message not found, skip
            if not isinstance(message_hash, six.string_types):
                continue

            # We have found a message

            # Message hash doesn't not match next string from stringset,
            # delete. Section start was marked at the top of this loop
            if (openstring is None or
                    openstring.template_replacement not in message_hash):
                try:
                    # If this is not the last key-value pair, delete up to
                    # (including) the next ','
                    #     ..., "a": {"message": "foo"}, ...
                    #          ^                       ^
                    #          |                       |
                    #        start                    end
                    delete_until = source.index(',', outer_value.end) + 1

                except ValueError:
                    # If this is the last key-value pair, delete up to (not
                    # including) the next '}':
                    #     ..., "a": {"message": "foo"}}
                    #          ^                      ^
                    #          |                      |
                    #        start                   end
                    delete_until = source.index('}', outer_value.end)
                transcriber.copy_until(delete_until + 1)
                transcriber.mark_section_end()
                transcriber.remove_section()
                continue

                if openstring.key != outer_key:  # pragma: no cover
                    # This should never happen
                    raise ParseError(u"Key '{}' from the database does not "
                                     u"match key '{}' from the template".
                                     format(openstring.key, outer_key))

            if (message_hash == openstring.template_replacement and
                    not openstring.pluralized):
                # Singular
                transcriber.copy_until(message_position)
                transcriber.add(openstring._strings[5])
                transcriber.skip(len(openstring.template_replacement))
            elif (openstring.template_replacement in message_hash and
                    openstring.pluralized):
                # Pluralized, preserve ICU formatting
                #   '{cnt, plural, <hash>}' ->
                #   '{cnt, plural, one {foo} other {foos}}'
                replacement_position = message_hash.find(
                    openstring.template_replacement
                )
                transcriber.copy_until(message_position + replacement_position)
                transcriber.add(icu_compiler.serialize_strings(
                    openstring.string, delimiter=' '
                ))
                transcriber.skip(len(openstring.template_replacement))
            else:  # pragma: no cover
                # This should never happen
                raise ParseError(u"Pluralized status of the string in the "
                                 u"template does not match the string's "
                                 u"status from the database, key: '{}'".
                                 format(openstring.key))
            openstring = next(stringset_iter, None)
        transcriber.copy_to_end()
        compiled = transcriber.get_destination()

        # Remove trailing ',', in case we deleted the last section
        compiled = re.sub(r',(\s*)}(\s*)$', r'\1}\2', compiled)

        return compiled

    @staticmethod
    def escape(string):
        return escape(string)

    @staticmethod
    def unescape(string):
        return unescape(string)
