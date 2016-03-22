from __future__ import absolute_import

import json
import re
from collections import OrderedDict

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.json import DumbJson


class JsonHandler_(object):
    name = "json"
    extension = "json"

    def parse(self, content):
        parsed = json.loads(content, object_pairs_hook=OrderedDict)
        assert isinstance(parsed, dict)

        template = OrderedDict()

        self.stringset = []

        self._extract_dict(parsed, nest=None, template=template)

        return json.dumps(template, indent=2), self.stringset

    def _extract_dict(self, parsed, nest, template):
        for key, value in parsed.iteritems():
            if nest is None:
                string_key = key
            else:
                string_key = "{}.{}".format(nest, key)
            if isinstance(value, unicode):
                string = OpenString(string_key, value)
                template[key] = string.template_replacement
                self.stringset.append(string)
            elif isinstance(value, dict):
                self._extract_dict(value,
                                   nest=string_key,
                                   template=template.setdefault(key,
                                                                OrderedDict()))
            elif isinstance(value, list):
                self._extract_list(value, nest=string_key,
                                   template=template.setdefault(key, []))

    def _extract_list(self, parsed, nest, template):
        for i, list_item in enumerate(parsed):
            string_key = "{}..{}..".format(nest, i)
            if isinstance(list_item, unicode):
                string = OpenString(string_key, list_item)
                self.stringset.append(string)
                template.append(string.template_replacement)
            elif isinstance(list_item, dict):
                template.append(OrderedDict())
                self._extract_dict(list_item, nest="{}..{}..".format(nest, i),
                                   template=template[-1])
            elif isinstance(list_item, list):
                template.append([])
                self._extract_list(list_item, nest="{}..{}..".format(nest, i),
                                   template=template[-1])

    def compile(self, template, stringset):
        parsed = json.loads(template, object_pairs_hook=OrderedDict)
        self.stringset = stringset
        self.stringset_index = 0

        self._intract(parsed)

        return json.dumps(parsed, indent=2)

    def _intract(self, parsed):
        if isinstance(parsed, dict):
            iterator = parsed.iteritems()
        elif isinstance(parsed, list):
            iterator = enumerate(parsed)

        to_delete = []
        for key, value in iterator:
            next_string = self._get_next_string()
            if isinstance(value, unicode):
                if (next_string and
                        next_string.template_replacement == value):
                    parsed[key] = next_string.string
                    self.stringset_index += 1
                else:
                    to_delete.append(key)
            else:
                all_deleted = self._intract(value)
                if all_deleted:
                    to_delete.append(key)

        all_deleted = len(to_delete) == len(parsed)

        for key in to_delete[::-1]:
            del parsed[key]

        return all_deleted

    def _get_next_string(self):
        try:
            return self.stringset[self.stringset_index]
        except IndexError:
            return None


class JsonHandler(Handler):
    name = "json"
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

        parsed = DumbJson(source)
        self.extract(parsed)
        self.transcriber.copy_until(len(source))

        return self.transcriber.get_destination(), self.stringset

    def extract(self, parsed, nest=None):
        if parsed.type == dict:
            for key, key_position, value, value_position in parsed:
                key = self._escape_key(key)
                if nest is not None:
                    key = "{}.{}".format(nest, key)
                if isinstance(value, unicode):
                    openstring = OpenString(key, value)
                    self.transcriber.copy_until(value_position)
                    self.transcriber.add(openstring.template_replacement)
                    self.transcriber.skip(len(value))
                    self.stringset.append(openstring)
                elif isinstance(value, DumbJson):
                    self.extract(value, key)
                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass
        elif parsed.type == list:
            for index, (item, item_position) in enumerate(parsed):
                if nest is None:
                    key = "..{}..".format(index)
                else:
                    key = "{}..{}..".format(nest, index)
                if isinstance(item, unicode):
                    openstring = OpenString(key, item)
                    self.transcriber.copy_until(item_position)
                    self.transcriber.add(openstring.template_replacement)
                    self.transcriber.skip(len(item))
                    self.stringset.append(openstring)
                elif isinstance(item, DumbJson):
                    self.extract(item, key)
                else:
                    # Ignore other JSON types (bools, nulls, numbers)
                    pass
        else:
            raise ParseError("Invalid JSON")

    @staticmethod
    def _escape_key(key):
        key = key.replace("\\", "\\\\")
        key = key.replace(".", "\\.")
        return key

    def compile(self, template, stringset):
        self.transcriber = Transcriber(template)
        template = self.transcriber.source
        self.stringset = stringset
        self.stringset_index = 0

        parsed = DumbJson(template)
        self.intract(parsed)

        self.transcriber.copy_until(len(template))
        compiled = self.transcriber.get_destination()

        return self.clean_compiled(compiled)

    def intract(self, parsed):
        at_least_one = False
        if parsed.type == dict:
            for key, key_position, value, value_position in parsed:
                self.transcriber.copy_until(key_position - 1)
                self.transcriber.mark_section_start()
                if isinstance(value, unicode):
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
                    all_removed = self.intract(value)
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

        elif parsed.type == list:
            for item, item_position in parsed:
                self.transcriber.copy_until(item_position - 1)
                self.transcriber.mark_section_start()
                if isinstance(item, unicode):
                    string = self._get_next_string()
                    if (string is not None and
                            item == string.template_replacement):
                        at_least_one = True
                        self.transcriber.copy_until(item_position)
                        self.transcriber.add(string.string)
                        self.transcriber.skip(len(item))
                        self.stringset_index += 1
                    else:
                        self.transcriber.copy_until(item_position +
                                                    len(item) + 1)
                        self.transcriber.mark_section_end()
                        self.transcriber.remove_section()
                elif isinstance(item, DumbJson):
                    all_removed = self.intract(item)
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

    def clean_compiled(self, compiled):
        "If sections were removed, clean leftover commas, brackets etc"
        while True:
            # First key-value of a dict was removed
            match = re.search(r'{\s*,', compiled)
            if match:
                compiled = "{}{{{}".format(compiled[:match.start()],
                                           compiled[match.end():])
                continue

            # Last key-value of a dict was removed
            match = re.search(r',\s*}', compiled)
            if match:
                compiled = "{}}}{}".format(compiled[:match.start()],
                                           compiled[match.end():])
                continue

            # First item of a list was removed
            match = re.search(r'\[\s*,', compiled)
            if match:
                compiled = "{}[{}".format(compiled[:match.start()],
                                          compiled[match.end():])
                continue

            # Last item of a list was removed
            match = re.search(r',\s*\]', compiled)
            if match:
                compiled = "{}]{}".format(compiled[:match.start()],
                                          compiled[match.end():])
                continue

            # Intermediate key-value of a dict or list was removed
            match = re.search(r',\s*,', compiled)
            if match:
                compiled = "{},{}".format(compiled[:match.start()],
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
