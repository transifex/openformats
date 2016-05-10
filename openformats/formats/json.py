# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import re
from itertools import count

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.json import DumbJson


class JsonHandler(Handler):
    name = "KEYVALUEJSON"
    extension = "json"

    def parse(self, content):
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

    @staticmethod
    def _escape_key(key):
        key = key.replace(u"\\", u"\\\\")
        key = key.replace(u".", u"\\.")
        return key

    def compile(self, template, stringset):
        # Lets play on the template first, we need it to not include the hashes
        # that aren't in the stringset. For that we will create a new stringset
        # which will have the hashes themselves as strings and compile against
        # that. The compilation process will remove any string sections that
        # are absent from the stringset. Next we will call `_clean_empties`
        # from the template to clear out any `...,  ,...` or `...{ ,...`
        # sequences left. The result will be used as the actual template for
        # the compilation process

        stringset = list(stringset)

        fake_stringset = [OpenString(openstring.key,
                                     openstring.template_replacement,
                                     order=openstring.order)
                          for openstring in stringset]
        new_template = self._replace_translations(template, fake_stringset)
        new_template = self._clean_empties(new_template)

        return self._replace_translations(new_template, stringset)

    def _replace_translations(self, template, stringset):
        self.transcriber = Transcriber(template)
        template = self.transcriber.source
        self.stringset = stringset
        self.stringset_index = 0

        parsed = DumbJson(template)
        self._intract(parsed)

        self.transcriber.copy_until(len(template))
        return self.transcriber.get_destination()

    def _intract(self, parsed):
        if parsed.type == dict:
            return self._intract_dict(parsed)
        elif parsed.type == list:
            return self._intract_list(parsed)

    def _intract_dict(self, parsed):
        at_least_one = False
        for key, key_position, value, value_position in parsed:
            self.transcriber.copy_until(key_position - 1)
            self.transcriber.mark_section_start()
            if isinstance(value, (str, unicode)):
                string = self._get_next_string()
                if (string is not None and
                        value == string.template_replacement):
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
                all_removed = self._intract(value)
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

    def _intract_list(self, parsed):
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
                all_removed = self._intract(item)
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

    @staticmethod
    def escape(string):
        escaped_string = string.replace('\\', r'\\').replace('"', '\\"')
        return escaped_string

    @staticmethod
    def unescape(string):
        unescaped_string = string.replace(r'\\', '\\').replace(r'\"', '"')
        return unescaped_string
