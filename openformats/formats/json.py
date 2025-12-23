# -*- coding: utf-8 -*-

from __future__ import absolute_import

import csv
import json
import re
from itertools import count
from typing import Tuple, Any

import six

from openformats.exceptions import ParseError
from openformats.handlers import Handler
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from openformats.utils.icu import ICUCompiler, ICUParser
from openformats.utils.json import DumbJson, escape, unescape

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

    PLURAL_ARG = "plural"
    PLURAL_KEYS_STR = " ".join(six.iterkeys(Handler._RULES_ATOI))

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

        if not self.stringset and self.name == "STRUCTURED_JSON":
            raise ParseError("No strings could be extracted")

        self.transcriber.copy_until(len(source))

        return self.transcriber.get_destination(), self.stringset

    def _extract(self, parsed, nest=None):
        if parsed.type == dict:
            for key, key_position, value, value_position in parsed:
                key = self._escape_key(key)
                if nest is not None:
                    key = f"{nest}.{key}"

                # 'key' should be unique
                if key in self.existing_keys:
                    # Need this for line number
                    self.transcriber.copy_until(key_position)
                    raise ParseError(
                        "Duplicate string key ('{}') in line {}".format(
                            key, self.transcriber.line_number
                        )
                    )
                self.existing_keys.add(key)

                if self.name == "STRUCTURED_JSON":
                    try:
                        ((string_value, _),) = value.find_children(self.STRING_KEY)
                    except Exception:
                        # Ignore other types of values like lists
                        pass
                    else:
                        if string_value:
                            if isinstance(
                                string_value, (six.binary_type, six.text_type)
                            ):
                                if string_value.strip():
                                    openstring = self._create_openstring(key, value)

                                    if openstring:
                                        self.stringset.append(openstring)
                            else:
                                # Need this for line number
                                self.transcriber.copy_until(key_position)
                                raise ParseError(
                                    "Invalid string value in line {}".format(
                                        self.transcriber.line_number
                                    )
                                )

                        elif isinstance(value, DumbJson):
                            self._extract(value, key)
                else:
                    if isinstance(value, (six.binary_type, six.text_type)):
                        if not value.strip():
                            continue

                        openstring = self._create_openstring(key, value, value_position)
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
                    key = f"..{index}.."
                else:
                    key = f"{nest}..{index}.."
                if isinstance(item, (six.binary_type, six.text_type)):
                    if not item.strip():
                        continue

                    openstring = self._create_openstring(key, item, item_position)
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

        return self._create_regular_string(key, value, value_position)

    def _create_pluralized_string(
        self, icu_string, value_position, context_value="", description_value=""
    ):
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
            context=context_value,
            developer_comment=description_value,
        )

        current_pos = icu_string.current_position
        string_to_replace = icu_string.string_to_replace

        self.transcriber.copy_until(value_position + current_pos)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(string_to_replace))

        return openstring

    def _create_regular_string(
        self, key, value, value_position, context_value="", description_value=""
    ):
        """Return a new simple OpenString based on the given key and value
        and update the transcriber accordingly.

        :param key: the string key
        :param value: the translation string
        :return: an OpenString or None
        """
        openstring = OpenString(
            key,
            value,
            order=next(self._order),
            context=context_value,
            developer_comment=description_value,
        )
        self.transcriber.copy_until(value_position)
        self.transcriber.add(openstring.template_replacement)
        self.transcriber.skip(len(value))

        return openstring

    @staticmethod
    def _escape_key(key):
        key = key.replace(
            DumbJson.BACKSLASH, "".join([DumbJson.BACKSLASH, DumbJson.BACKSLASH])
        )
        key = key.replace(".", "".join([DumbJson.BACKSLASH, "."]))
        return key

    @staticmethod
    def _unescape_key(key):
        key = key.replace(DumbJson.BACKSLASH + DumbJson.BACKSLASH, DumbJson.BACKSLASH)
        key = key.replace(DumbJson.BACKSLASH + ".", ".")
        return key

    def compile(self, template, stringset, **kwargs):
        stringset = list(stringset)
        return self._replace_translations(
            template,
            stringset,
            is_real_stringset=True,
        )

    def _replace_translations(self, template, stringset, is_real_stringset):
        self.transcriber = Transcriber(template)
        template = self.transcriber.source

        self.stringset = stringset
        self.stringset_index = 0

        self.metadata_blocks = []

        parsed = DumbJson(template)
        self._insert(parsed, is_real_stringset)

        self.transcriber.copy_until(len(template))
        return self.transcriber.get_destination()

    def remove_strings_from_template(self, template, stringset, **kwargs):
        """
        Remove strings from the template that are not in the stringset.
        """
        fake_stringset = [
            OpenString(
                openstring.key,
                openstring.template_replacement,
                order=openstring.order,  # type: ignore
                pluralized=openstring.pluralized,
            )
            for openstring in stringset
        ]
        updated_template = self._replace_translations(
            template,
            fake_stringset,
            is_real_stringset=False,
        )
        return self._clean_empties(updated_template)

    def add_strings_to_template(self, template, stringset, **kwargs):
        """
        Add entries that do not exist in the template with minimal conditional logic.
        """
        remaining = stringset[self.stringset_index :]  # type: ignore
        if not remaining:
            return template

        strings_to_add = list(remaining)

        transcriber = Transcriber(template)
        source = transcriber.source
        parsed = DumbJson(source)

        container_type = self._get_root(parsed)
        items = list(parsed)
        had_items = bool(items)

        # Detect style
        multiline = "\n" in source[parsed.start : parsed.end + 1]

        # Find insertion point
        insertion_point = parsed.end
        if multiline:
            # Insert before last newline if present
            i = insertion_point - 1
            while i >= 0 and source[i] in (" ", "\t"):
                i -= 1
            if i >= 0 and source[i] == "\n":
                insertion_point = i

        # Build entries
        entries = []
        for os in strings_to_add:
            if container_type == dict:
                entries.append(self._make_added_entry_for_dict(os))
            else:
                entries.append(self._make_added_entry_for_list(os))

        # Format insertion based on style
        if multiline:
            joined = ",\n  ".join(entries)
            if had_items:
                insertion = f",\n  {joined}"
            else:
                insertion = f"\n  {joined}"
        else:
            joined = ", ".join(entries)
            if had_items:
                insertion = f", {joined}"
            else:
                insertion = f" {joined} "

        # Insert
        transcriber.copy_until(insertion_point)
        transcriber.add(insertion)
        transcriber.copy_to_end()

        return transcriber.get_destination()

    def _get_root(self, parsed):
        """
        Determine which DumbJson node (dict or list) should receive new entries.
        Returns the container node and its type.
        """
        if parsed.type == dict:
            return dict

        if parsed.type == list:
            return list

        raise ParseError("Template must be a JSON object or array")

    def _make_added_entry_for_dict(self, os):
        """
        Build the JSON snippet for a *single* added OpenString at top level.

        Subclasses can override this to change the structure of the value.

        Note:
        - We unescape the key to match file uploaded keys behavior. Specifically,
        when uploading a file with a key like 'key \b', this is escaped during parse
        and gets saved in the db as 'key \\b'. Then it gets compiled as 'key \b'.
        In the same, when a string is added from the editor we escape the key and similarly
        to the above logic, we need it unescaped on compile.
        """
        return f'"{self._unescape_key(os.key)}": "{os.template_replacement}"'

    def _make_added_entry_for_list(self, os):
        return json.dumps(
            {self._unescape_key(os.key): os.template_replacement},
            ensure_ascii=False,
        )

    def _insert(self, parsed, is_real_stringset):
        if parsed.type == dict:
            return self._insert_from_dict(parsed, is_real_stringset)
        elif parsed.type == list:
            return self._insert_from_list(parsed, is_real_stringset)

    def _insert_item(self, value, value_position, is_real_stringset):
        at_least_one = False

        if isinstance(value, (six.binary_type, six.text_type)):
            if value.strip():
                string = self._get_next_string()
                string_exists = string is not None

                templ_replacement = (
                    string.template_replacement if string_exists else None
                )

                # Pluralized string
                if string_exists and string.pluralized and templ_replacement in value:
                    at_least_one = True
                    self._insert_plural_string(
                        value, value_position, string, is_real_stringset
                    )

                # Regular string
                elif string_exists and value == templ_replacement:
                    at_least_one = True
                    self._insert_regular_string(value, value_position, string.string)

                else:
                    # Anything else: just remove the current section
                    self._copy_until_and_remove_section(value_position + len(value) + 1)
            else:
                # value is an empty string, add the key but don't update
                # stringset_index
                at_least_one = True

                if len(value) > 0:
                    # Add whitespace back
                    self._insert_regular_string(value, value_position, value, False)
                else:
                    at_least_one = True
                    self._insert_regular_string(value, value_position, "", False)

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
            if (
                key.startswith("@")
                and key != ("@@locale")
                and isinstance(value, (six.binary_type, six.text_type))
            ):
                self.metadata_blocks.append(
                    (key_position - 1, value_position + len(value) + 1)
                )

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

    def _insert_plural_string(self, value, value_position, string, is_real_stringset):
        templ_replacement = string.template_replacement
        replacement_pos = value.find(templ_replacement)

        if is_real_stringset:
            replacement = ICUCompiler().serialize_strings(string.string, delimiter=" ")
        else:
            replacement = templ_replacement

        self.transcriber.copy_until(value_position + replacement_pos)
        self.transcriber.add(replacement)

        self.transcriber.skip(len(templ_replacement))
        self.transcriber.copy(len(value) - replacement_pos - len(templ_replacement))
        self.stringset_index += 1

    def _insert_regular_string(
        self, value, value_position, string, update_stringset_index=True
    ):
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
        """If sections were removed, clean leftover commas, brackets etc.

        Eg:
            '{"a": "b", ,"c": "d"}' -> '{"a": "b", "c": "d"}'
            '{, "a": "b", "c": "d"}' -> '{"a": "b", "c": "d"}'
            '["a", , "b"]' -> '["a", "b"]'
        """
        while True:
            # First key-value of a dict was removed
            match = re.search(r"{\s*,", compiled)
            if match:
                compiled = "{}{{{}".format(
                    compiled[: match.start()], compiled[match.end() :]
                )
                continue

            # Last key-value of a dict was removed
            match = re.search(r",\s*}", compiled)
            if match:
                compiled = "{}}}{}".format(
                    compiled[: match.start()], compiled[match.end() :]
                )
                continue

            # First item of a list was removed
            match = re.search(r"\[\s*,", compiled)
            if match:
                compiled = "{}[{}".format(
                    compiled[: match.start()], compiled[match.end() :]
                )
                continue

            # Last item of a list was removed
            match = re.search(r",\s*\]", compiled)
            if match:
                compiled = "{}]{}".format(
                    compiled[: match.start()], compiled[match.end() :]
                )
                continue

            # Intermediate key-value of a dict or list was removed
            match = re.search(r",\s*,", compiled)
            if match:
                compiled = "{},{}".format(
                    compiled[: match.start()], compiled[match.end() :]
                )
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


class ArbHandler(JsonHandler):
    name = "ARB"
    extension = "arb"
    keep_sections = True

    def parse(self, content, **kwargs):
        # Validate that content is JSON
        self.validate_content(content)

        self.transcriber = Transcriber(content)
        source = self.transcriber.source
        self.stringset = []
        self.existing_keys = set()
        self.metadata = dict()

        try:
            parsed = DumbJson(source)
        except ValueError as e:
            raise ParseError(six.text_type(e))
        if parsed.type != dict:
            raise ParseError("Invalid JSON")
        self._order = count()
        self._find_keys(parsed)
        self._extract(parsed)

        if not self.stringset:
            raise ParseError("No strings could be extracted")

        self.transcriber.copy_until(len(source))

        return self.transcriber.get_destination(), self.stringset

    def _find_keys(self, parsed, nest=None):
        for key, key_position, value, _ in parsed:
            key = self._escape_key(key)
            if nest is not None:
                key = f"{nest}.{key}"

            # 'key' should be unique
            if key in self.existing_keys:
                # Need this for line number
                self.transcriber.copy_until(key_position)
                raise ParseError(
                    "Duplicate string key ('{}') in line {}".format(
                        key, self.transcriber.line_number
                    )
                )
            if nest is None:  # store all root-level keys in order to detect duplication
                self.existing_keys.add(key)
            elif key.startswith("@"):
                if key.endswith(".type") and value != "text":
                    self.existing_keys.add(key)
                elif key.endswith(".context"):
                    self.metadata[key] = value
                elif key.endswith(".description"):
                    self.metadata[key] = value

            if isinstance(value, DumbJson):
                self._find_keys(value, key)
            else:
                pass

    def _extract(self, parsed):
        for key, _, value, value_position in parsed:
            key = self._escape_key(key)

            if key.startswith("@"):
                continue
            elif isinstance(value, (six.text_type)):
                if not value.strip():
                    continue
                elif f"@{key}.type" in self.existing_keys:
                    continue

                context_key = f"@{key}.context"
                context_value = (
                    self.metadata[context_key]
                    if context_key in self.metadata.keys()
                    else ""
                )
                description_key = f"@{key}.description"
                description_value = (
                    self.metadata[description_key]
                    if description_key in self.metadata.keys()
                    else ""
                )

                openstring = self._create_openstring(
                    key, value, value_position, context_value, description_value
                )
                if openstring:
                    self.stringset.append(openstring)
            else:
                # Ignore other JSON types (bools, nulls, numbers)
                pass

    def _create_openstring(
        self, key, value, value_position, context_value, description_value
    ):
        parser = ICUParser(allow_numeric_plural_values=True)
        icu_string = parser.parse(key, value)
        if icu_string and any(
            (string.strip() == "" for string in icu_string.strings_by_rule.values())
        ):
            return
        if icu_string:
            return self._create_pluralized_string(
                icu_string, value_position, context_value, description_value
            )

        return self._create_regular_string(
            key, value, value_position, context_value, description_value
        )

    def compile(self, template, stringset, language_info=None, **kwargs):
        # Lets play on the template first, we need it to not include the hashes
        # that aren't in the stringset. For that we will create a new stringset
        # which will have the hashes themselves as strings and compile against
        # that. The compilation process will remove any string sections that
        # are absent from the stringset. Next we will call `_clean_empties`
        # from the template to clear out any `...,  ,...` or `...{ ,...`
        # sequences left. The result will be used as the actual template for
        # the compilation process
        self.keep_sections = kwargs.get("keep_sections", True)

        stringset = list(stringset)

        if language_info is not None:
            match = re.search(r"(\"@@locale\"\s*:\s*\")([A-Z_a-z]*)\"", template)
            if match:
                template = "{}{}{}".format(
                    template[: match.start(2)],
                    language_info["code"],
                    template[match.end(2) :],
                )

        return self._replace_translations(template, stringset, True)

    def sync_template(
        self, template: str, stringset: list[OpenString], **kwargs: Any
    ) -> str:
        stringset = list(stringset)
        self.keep_sections = kwargs.get("keep_sections", True)
        template = self.remove_strings_from_template(template, stringset, **kwargs)
        return template

    def _copy_until_and_remove_section(self, pos):
        """
        Copy characters to the transcriber until the given position,
        then end the current section.
        """
        self.transcriber.copy_until(pos)
        self.transcriber.mark_section_end()
        # Unlike the JSON format, do not remove the remaining section of the template
        if self.keep_sections == False:  # needed for a test
            self.transcriber.remove_section()


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
    STRUCTURE_FIELDS = {CONTEXT_KEY, DEVELOPER_COMMENT_KEY, CHARACTER_LIMIT_KEY}

    def compile(self, template, translations, **kwargs):
        self.translations = iter(translations)
        self.transcriber = Transcriber(template)
        template = self.transcriber.source

        dumb_template = DumbJson(template)
        self._compile_recursively(dumb_template)
        self.transcriber.copy_to_end()
        return self.transcriber.get_destination()

    def _compile_value(self, value, template_value, value_position, skip=False):
        value = template_value if skip else value

        if value is not None:
            if value == "" and template_value is None:
                self.transcriber.add("null")
            else:
                if template_value is None:
                    self.transcriber.add(f'"{value}"')
                else:
                    self.transcriber.add(f"{value}")
        else:
            self.transcriber.add("null")

        self.transcriber.skip(len(f"{template_value}"))
        self.transcriber.copy_until(value_position + len(f"{template_value}") + 1)

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
                    (value, _) = current_part.find_children(self.STRING_KEY)[0]
                    if not value.strip():
                        translation = OpenString("", value)
                        skip = True
                    else:
                        translation = next(self.translations, None)
                        skip = False

                    context_added = False
                    character_limit_added = False
                    developer_comments_added = False

                    line_separator = None
                    key_value_separator = None
                    for key, key_position, value, value_position in current_part:
                        prev_position_end = self.transcriber.ptr
                        line_separator = current_part.source[
                            prev_position_end + 1 : key_position - 1
                        ]
                        key_value_separator = current_part.source[
                            key_position + len(key) : value_position - 1
                        ]
                        self.transcriber.copy_until(key_position - 1)
                        self.transcriber.copy_until(value_position)
                        if key == self.CONTEXT_KEY and translation:
                            context = translation.context
                            self._compile_value(
                                self.escape(context), value, value_position, skip=skip
                            )
                            context_added = True
                        elif key == self.DEVELOPER_COMMENT_KEY and translation:
                            developer_comment = translation.developer_comment
                            self._compile_value(
                                self.escape(developer_comment),
                                value,
                                value_position,
                                skip=skip,
                            )
                            developer_comments_added = True
                        elif key == self.CHARACTER_LIMIT_KEY and translation:
                            character_limit = translation.character_limit
                            self._compile_value(
                                character_limit, value, value_position, skip=skip
                            )
                            character_limit_added = True
                        elif key == self.STRING_KEY and translation:
                            if translation.pluralized:
                                string_replacement = ICUCompiler().serialize_strings(
                                    translation.string, delimiter=" "
                                )
                                string_replacement = value.replace(
                                    translation.template_replacement,
                                    string_replacement,
                                )
                            else:
                                string_replacement = translation.string
                            self._compile_value(
                                string_replacement, value, value_position
                            )
                        elif not isinstance(value, DumbJson):
                            self.transcriber.copy_until(
                                value_position + len(f"{value}") + 1
                            )

                    extra_elements = []
                    if not context_added and translation and translation.context:
                        extra_elements.append(
                            '"{}{}"{}"'.format(
                                "context",
                                key_value_separator,
                                self.escape(translation.context),
                            )
                        )
                    if (
                        not character_limit_added
                        and translation
                        and translation.character_limit
                    ):
                        extra_elements.append(
                            '"{}{}{}'.format(
                                "character_limit",
                                key_value_separator,
                                translation.character_limit,
                            )
                        )
                    if (
                        not developer_comments_added
                        and translation
                        and translation.developer_comment
                    ):
                        extra_elements.append(
                            '"{}{}"{}"'.format(
                                "developer_comment",
                                key_value_separator,
                                self.escape(translation.developer_comment),
                            )
                        )
                    if extra_elements:
                        self.transcriber.add(
                            ","
                            + line_separator
                            + ("," + line_separator).join(extra_elements)
                        )

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
        ((string_value, _),) = payload_dict.find_children(self.STRING_KEY)
        icu_string = parser.parse(key, string_value)
        if icu_string:
            return self._create_pluralized_string(icu_string, payload_dict)

        return self._create_regular_string(key, payload_dict)

    def _create_pluralized_string(self, icu_string, payload_dict):
        """Create a pluralized string based on the given information.

        Also updates the transcriber accordingly.

        :param ICUString icu_string: The ICUString object that will generate
            the pluralized string
        "param DumbJson payload_dict: the string and metadata
        :return: an OpenString object
        :rtype: OpenString
        """
        ((_, string_position),) = payload_dict.find_children(self.STRING_KEY)
        payload_dict = json.loads(
            payload_dict.source[payload_dict.start : payload_dict.end + 1]
        )
        comment_value = payload_dict.get(self.DEVELOPER_COMMENT_KEY)
        limit_value = payload_dict.get(self.CHARACTER_LIMIT_KEY)
        context_value = payload_dict.get(self.CONTEXT_KEY)

        openstring = OpenString(
            icu_string.key,
            icu_string.strings_by_rule,
            pluralized=icu_string.pluralized,
            order=next(self._order),
            developer_comment=comment_value or "",
            character_limit=limit_value,
            context=context_value or "",
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
        ((string_value, string_position),) = payload_dict.find_children(self.STRING_KEY)
        payload_dict = json.loads(
            payload_dict.source[payload_dict.start : payload_dict.end + 1]
        )
        comment_value = payload_dict.get(self.DEVELOPER_COMMENT_KEY)
        limit_value = payload_dict.get(self.CHARACTER_LIMIT_KEY)
        context_value = payload_dict.get(self.CONTEXT_KEY)

        openstring = OpenString(
            key,
            string_value,
            order=next(self._order),
            developer_comment=comment_value or "",
            character_limit=limit_value,
            context=context_value or "",
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
        if not key.endswith(f".{self.STRING_KEY}"):
            return None
        # Remove the STRING_KEY part of the key as it is not needed. Add +1
        # when calculating the length of the STRING_KEY, for the "." character
        return key[: -(len(self.STRING_KEY) + 1)]

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
        return {
            field: (
                json_dict[field] if field in json_dict else OpenString.DEFAULTS[field]
            )
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
            csv.reader(StringIO(key), delimiter=".", escapechar="\\")
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

    def remove_strings_from_template(self, template, stringset, **kwargs):
        """
        Remove structured-json entries whose hashed 'string' content does not
        match the ordered stringset, similar to JsonHandler behavior, but:

        - We match by OpenString.template_replacement (hash), not by key.
        - For dict roots: walk nested dicts and drop leaf objects with
          mismatching "string".
        - For list roots: treat each list item as a dict-root, dropping
          items that end up with no kept leaves.
        """
        self.stringset = list(stringset)
        self.stringset_index = 0

        transcriber = Transcriber(template)
        source = transcriber.source
        parsed = DumbJson(source)

        def next_string():
            try:
                return self.stringset[self.stringset_index]
            except IndexError:
                return None

        def walk_dict(node):
            """
            Recursively traverse a DumbJson dict node.

            Returns True if this node (or any of its descendants) contains at
            least one *kept* leaf. Otherwise returns False so the caller can
            prune the whole section.
            """
            if node.type != dict:
                return False

            has_kept_leaf = False

            for _, key_pos, value, _ in node:
                if not (isinstance(value, DumbJson) and value.type == dict):
                    continue

                # Decide if this object is a *leaf* (direct "string" field)
                is_leaf = any(
                    child_key == self.STRING_KEY for child_key, _, _, _ in value
                )

                transcriber.copy_until(key_pos - 1)
                transcriber.mark_section_start()

                if is_leaf:
                    ((string_value, _),) = value.find_children(self.STRING_KEY)

                    current = next_string()
                    keep = False

                    if current is not None:
                        templ = current.template_replacement

                        if current.pluralized:
                            # hash embedded inside ICU plural string
                            if templ in string_value:
                                keep = True
                        else:
                            # plain hash
                            if string_value == templ:
                                keep = True

                    transcriber.copy_until(value.end + 1)
                    transcriber.mark_section_end()

                    if keep:
                        has_kept_leaf = True
                        self.stringset_index += 1
                    else:
                        transcriber.remove_section()
                else:
                    # Nested dict – recurse
                    child_has_kept = walk_dict(value)

                    transcriber.copy_until(value.end + 1)
                    transcriber.mark_section_end()

                    if child_has_kept:
                        has_kept_leaf = True
                    else:
                        transcriber.remove_section()

            return has_kept_leaf

        if parsed.type == dict:
            walk_dict(parsed)
        elif parsed.type == list:
            # List-root: each item is a dict-root
            for value, _ in parsed:
                if not isinstance(value, DumbJson) or value.type != dict:
                    continue

                transcriber.copy_until(value.start)
                transcriber.mark_section_start()

                has_kept = walk_dict(value)

                transcriber.copy_until(value.end + 1)
                transcriber.mark_section_end()

                if not has_kept:
                    transcriber.remove_section()

        transcriber.copy_until(len(source))
        compiled = transcriber.get_destination()
        return self._clean_empties(compiled)

    def _build_structured_payload(self, os) -> dict:
        """
        Build the inner payload dict for a structured-json entry:

            {
              "string": "<hash>",
              "context": "...",
              "developer_comment": "...",
              "character_limit": 100
            }
        """
        payload = {
            self.STRING_KEY: os.template_replacement,
        }

        # Optional metadata – only add if present
        if getattr(os, "context", None):
            payload[self.CONTEXT_KEY] = self.escape(os.context)
        if getattr(os, "developer_comment", None):
            payload[self.DEVELOPER_COMMENT_KEY] = self.escape(os.developer_comment)
        if getattr(os, "character_limit", None) is not None:
            payload[self.CHARACTER_LIMIT_KEY] = os.character_limit

        return payload

    def _build_structured_json_entry(self, os) -> Tuple[str, str]:
        """
        Build the JSON snippet for a structured-json entry for dict roots:

            "key": {
              "string": "<hash>",
              "context": "...",
              "developer_comment": "...",
              "character_limit": 100
            }

        Note:
        - We unescape the key to match file uploaded keys behavior. Specifically,
        when uploading a file with a key like 'key \b', this is escaped during parse
        and gets saved in the db as 'key \\b'. Then it gets compiled as 'key \b'.
        In the same, when a string is added from the editor we escape the key and similarly
        to the above logic, we need it unescaped on compile.
        """
        key_literal = f'"{self._unescape_key(os.key)}"'
        payload = self._build_structured_payload(os)

        value_literal = json.dumps(payload, ensure_ascii=False, indent=2)

        # Optional cosmetic tab indent after the first line
        lines = value_literal.splitlines()
        if len(lines) > 1:
            lines = [lines[0]] + ["\t" + line for line in lines[1:]]
        value_literal = "\n".join(lines)

        return key_literal, value_literal

    def _make_added_entry_for_dict(self, os) -> str:
        key_literal, value_literal = self._build_structured_json_entry(os)
        return f"{key_literal}: {value_literal}"

    def _make_added_entry_for_list(self, os) -> str:
        """
        For list-root STRUCTURED_JSON, each added item is a *separate object*
        in the root list, with a single top-level key.

        The key is taken *as-is* from os.key (no '..0..' stripping, no
        special dot handling):

            os.key = "batmobil"

        Resulting list item:

            {
              "batmobil": {
                "string": "<hash>",
                "context": "...",
                "developer_comment": "...",
                "character_limit": 100
              }
            }
        """
        container = {self._unescape_key(os.key): self._build_structured_payload(os)}

        return json.dumps(container, ensure_ascii=False, indent=2)


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
        return self._replace_translations(template, stringset, is_real_stringset=True)

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
        key_split = key.split(".")
        try:
            return self.json_dict[key_split[0]]["description"]
        except KeyError:
            return ""

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

    def remove_strings_from_template(
        self,
        template: str,
        stringset: list[OpenString],
        **kwargs,
    ) -> str:
        """
        Removes strings from the template that are not in the stringset.
        """
        return template

    def add_strings_to_template(
        self, template: str, stringset: list[OpenString], **kwargs: Any
    ) -> str:
        """
        Adds strings to the template that are not in the template currently.
        """
        return template


class ChromeI18nHandlerV3(Handler):
    """New version of chrome-json handler.

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
            raise ParseError("Source file must be a JSON object")

        # Main loop
        for outer_key, outer_key_position, outer_value, outer_value_position in parsed:
            if outer_key in existing_keys:
                transcriber.copy_until(outer_key_position)
                raise ParseError(
                    f"Key '{outer_key}' appears multiple times (line {transcriber.line_number})"
                )
            existing_keys.add(outer_key)

            if not isinstance(outer_value, DumbJson):
                continue
            if outer_value.type != dict:
                continue

            # Figure out message and description
            (message, message_position), (description, _) = outer_value.find_children(
                "message", "description"
            )
            if not isinstance(message, six.string_types):
                continue
            if not isinstance(description, six.string_types):
                description = None

            # Extract string
            icu_string = icu_parser.parse(outer_key, message)
            if icu_string:
                # Pluralized
                openstring = OpenString(
                    icu_string.key,
                    icu_string.strings_by_rule,
                    pluralized=icu_string.pluralized,
                    order=next(_order),
                    developer_comment=description or "",
                )
                # Preserve ICU formatting:
                #   '{cnt, plural, one {foo} other {foos}}' ->
                #   '{cnt, plural, <hash>}'
                transcriber.copy_until(message_position + icu_string.current_position)
                transcriber.add(openstring.template_replacement)
                transcriber.skip(len(icu_string.string_to_replace))
            else:
                # Singular
                openstring = OpenString(
                    outer_key,
                    message,
                    order=next(_order),
                    developer_comment=description or "",
                )
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
        for outer_key, outer_key_position, outer_value, outer_value_position in parsed:
            # Mark section start in case we want to delete this section
            transcriber.copy_until(outer_key_position - 1)
            transcriber.mark_section_start()

            # Not something we extracted a string from, skip
            if not isinstance(outer_value, DumbJson):
                continue
            if outer_value.type != dict:
                continue

            # Find message
            ((message_hash, message_position),) = outer_value.find_children("message")

            # Message not found, skip
            if not isinstance(message_hash, six.string_types):
                continue

            # We have found a message

            # Message hash doesn't not match next string from stringset,
            # delete. Section start was marked at the top of this loop
            if (
                openstring is None
                or openstring.template_replacement not in message_hash
            ):
                try:
                    # If this is not the last key-value pair, delete up to
                    # (including) the next ','
                    #     ..., "a": {"message": "foo"}, ...
                    #          ^                       ^
                    #          |                       |
                    #        start                    end
                    delete_until = source.index(",", outer_value.end) + 1

                except ValueError:
                    # If this is the last key-value pair, delete up to (not
                    # including) the next '}':
                    #     ..., "a": {"message": "foo"}}
                    #          ^                      ^
                    #          |                      |
                    #        start                   end
                    delete_until = source.index("}", outer_value.end)
                transcriber.copy_until(delete_until + 1)
                transcriber.mark_section_end()
                transcriber.remove_section()
                continue

                if openstring.key != outer_key:  # pragma: no cover
                    # This should never happen
                    raise ParseError(
                        "Key '{}' from the database does not "
                        "match key '{}' from the template".format(
                            openstring.key, outer_key
                        )
                    )

            if (
                message_hash == openstring.template_replacement
                and not openstring.pluralized
            ):
                # Singular
                transcriber.copy_until(message_position)
                transcriber.add(openstring._strings[5])
                transcriber.skip(len(openstring.template_replacement))
            elif (
                openstring.template_replacement in message_hash
                and openstring.pluralized
            ):
                # Pluralized, preserve ICU formatting
                #   '{cnt, plural, <hash>}' ->
                #   '{cnt, plural, one {foo} other {foos}}'
                replacement_position = message_hash.find(
                    openstring.template_replacement
                )
                transcriber.copy_until(message_position + replacement_position)
                transcriber.add(
                    icu_compiler.serialize_strings(openstring.string, delimiter=" ")
                )
                transcriber.skip(len(openstring.template_replacement))
            else:  # pragma: no cover
                # This should never happen
                raise ParseError(
                    "Pluralized status of the string in the "
                    "template does not match the string's "
                    "status from the database, key: '{}'".format(openstring.key)
                )
            openstring = next(stringset_iter, None)
        transcriber.copy_to_end()
        compiled = transcriber.get_destination()

        # Remove trailing ',', in case we deleted the last section
        compiled = re.sub(r",(\s*)}(\s*)$", r"\1}\2", compiled)

        return compiled

    @staticmethod
    def escape(string):
        return escape(string)

    @staticmethod
    def unescape(string):
        return unescape(string)
