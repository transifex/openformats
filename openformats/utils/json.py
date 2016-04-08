from __future__ import absolute_import

import json
import re


class DumbJson(object):
    """ A utility to help iterate over a JSON string. The main focuses are:

        1. Return the exact contents of each encountered string, don't unescape
           double quotes ('"')
        2. Also return the positions of things encountered

        To initialize, simply pass a JSON string:

            >>> dumb_json = DumbJson('{"hello": "world"}')

        If you want, you can pass an extra argument to identify an embedded
        JSON object within the outer one. For example, if you have this string.

            >>> source = '["first string", {"second": "dict"}, "third string"]'

        You can:

            >>> start = source.index('{')  # 17
            >>> dumb_json = DumbJson(source, start)

        In this case, when you iterate over this, it will only yield the inner
        dictionary (`{"second": "string"}`). The item positions yielded while
        iterating will be in respect to the outer string, so:

            >>> assert list(dumb_json) == [('second', 19, 'dict', 29)]

        If the DumbJson object is a dictionary, then iterating it will yield
        4-tuples with `(key, key_position, value, value_position)`. If it's a
        list it will yield 2-tuples with `(item, item_position)`. Eg:

            >>> assert list(DumbJson('{"a": "b"}')) == [('a', 2, 'b', 7)]
            >>> assert list(DumbJson('["a", "b"]')) == [('a', 2), ('b', 7)]

        Encountering an embedded JSON structure while iterating will yield a
        DumbJson object:

            >>> embedded, _ = list(DumbJson('[["a"]]'))[0]
            >>> assert isinstance(embedded, DumbJson)
            >>> assert list(embedded) == [("a", 3)]

            # Note that the position (3) is in respect to the root JSON string

        When the items or values are not strings but objects allowed by JSON,
        like numbers, booleans or null, they will be yielded normally:

            >>> assert list(DumbJson('{"a": null}')) == [("a", 2, None, 6)]
            >>> assert list(DumbJson('[null]')) == [(None, 2)]
    """

    def __init__(self, source, start=0):
        self.source = source
        self._end = None
        starting_symbol, self.start = self._find_next('{[', start)
        if starting_symbol == '{':
            self.type = dict
        elif starting_symbol == '[':
            self.type = list
        else:
            raise ValueError("Input is not a JSON container")

    def __iter__(self):
        if self.type == dict:
            return self._iter_dict()
        elif self.type == list:
            return self._iter_list()

    def _iter_dict(self):
        # The '_p' suffix means 'position'

        start = self.start + 1

        # Maybe it's an empty dict
        end, end_p = self._find_next('"}', start)
        if end == "}":
            self.end = end_p
            return

        while True:
            # Lets find our key
            _, start_key_quote_p = self._find_next('"', start)
            key_p = start_key_quote_p + 1
            _, end_key_quote_p = self._find_next('"', key_p,
                                                 require_whitespace=False)
            key = self.source[key_p:end_key_quote_p]
            _, colon_p = self._find_next(':', end_key_quote_p + 1)
            value_start_string, value_start_computed, value_start_p =\
                self._process_value(colon_p + 1)

            # Our job in each case is to yield something and set 'next_p' to
            # where we should search for our next item
            if value_start_string == '"':
                # We found a string!
                value_p = value_start_p + 1
                _, value_end_quote_p = self._find_next(
                    '"', value_p, require_whitespace=False
                )
                value = self.source[value_p:value_end_quote_p]
                yield key, key_p, value, value_p
                next_p = value_end_quote_p + 1
            elif value_start_string in ('{', '['):
                # We found an embedded, lets return an instance of ourself
                embedded = DumbJson(self.source, value_start_p)
                yield key, key_p, embedded, value_start_p
                next_p = embedded.end + 1
            elif (value_start_computed is not None or
                    value_start_string == "null"):
                # We found something else allowed by JSON
                yield key, key_p, value_start_computed, value_start_p
                next_p = value_start_p + len(value_start_string)
            else:
                # Something went wrong
                raise ValueError("No JSON value could be decoded")

            next_symbol, next_symbol_p = self._find_next(',}', next_p)
            if next_symbol == ',':
                start = next_symbol_p + 1
            elif next_symbol == '}':
                self.end = next_symbol_p
                break

    def _iter_list(self):
        # The '_p' suffix means 'position'

        start = self.start + 1

        # Maybe it's an empty list
        match = re.search(r'^\s*.', self.source[start:])
        if match:
            if match.group()[-1] == "]":
                self.end = start + match.end() - 1
                return

        while True:
            # Lets find our items
            item_start_string, item_start_computed, item_start_p =\
                self._process_value(start)

            # Our job in each case is to yield something and set 'next_p' to
            # where we should search for our next item
            if item_start_string == '"':
                # We found a string!
                item_p = item_start_p + 1
                _, end_item_quote_p = self._find_next('"', item_p,
                                                      require_whitespace=False)
                item = self.source[item_p:end_item_quote_p]
                yield item, item_p
                next_p = end_item_quote_p + 1
            elif item_start_string in ('{', '['):
                # We found an embedded, lets return an instance of ourself
                embedded = DumbJson(self.source, item_start_p)
                yield embedded, item_start_p
                next_p = embedded.end + 1
            elif (item_start_computed is not None or
                    item_start_string == "null"):
                # We found something else allowed by JSON
                yield item_start_computed, item_start_p
                next_p = item_start_p + len(item_start_string)
            else:
                # Something went wrong
                raise ValueError("No JSON value could be decoded")

            next_symbol, next_symbol_p = self._find_next(',]', next_p)
            if next_symbol == ',':
                start = next_symbol_p + 1
            elif next_symbol == ']':
                self.end = next_symbol_p
                break

    def _find_next(self, symbols, start=0, require_whitespace=True):
        symbols = {s for s in symbols}
        for ptr in xrange(start, len(self.source)):
            candidate = self.source[ptr]
            if candidate in symbols:
                if (candidate == '"' and ptr > 0 and
                        self.source[ptr - 1] == '\\'):
                    continue
                return candidate, ptr
            if require_whitespace and not candidate.isspace():
                newline_count = self.source.count('\n', 0, ptr)
                raise ValueError(
                    u"Was expecting whitespace or one of `{symbols}` on line "
                    u"{line_no}, found `{candidate}` instead".format(
                        symbols=''.join(symbols),
                        line_no=newline_count + 1,
                        candidate=candidate,
                    )
                )
        return None, None

    def _process_value(self, start):
        """ A variation of _find_next. If the next non-empty character after
            `start` is in ('"', '{', '['), this will behave exactly like
            `_find_next('"{[', start)`. If the next non empty sequence after
            `start` is a number, bolean or 'null', it will return appropriate
            values.

            Returns 3 values:
            - value_start_string: in case of ('"', '{', '['), it is the same as
              the first return value of _find_next. Otherwise, it's the string
              representation of whatever the value is (the actual string "true"
              or "3.14159")
            - value_start_computed: in case of ('"', '{', '['), it is
              irrelevant (None), otherwise it's the computed value
            - value_start_p: where the value, whatever it is, is encountered
        """

        # Lets construct a regular expression to find the first non-empty char
        value_pat = r'{dict_list_string}|{true_false_null}|{e_notation}|'\
            r'{_float}|{integer}'.format(
                dict_list_string=r'[{\["]',
                true_false_null=r'true|false|null',
                e_notation=r'-?\d+e-?\d+',
                _float=r'-?\d+\.\d+',
                integer=r'-?\d+',
            )
        first_non_empty = r'^(?P<spaces>\s*)(?P<value>{})'.format(value_pat)
        match = re.search(first_non_empty, self.source[start:])
        # We probably found a match, otherwise this is not JSON
        if match:
            spaces, value = match.groups()
            value_start = start + len(spaces)
            if value in ('{', '[', '"'):
                return value, None, value_start
            else:
                # We either have true/false/null or a number of sorts
                return value, json.loads(value), value_start
        else:
            raise ValueError("No JSON value could be decoded")

    @property
    def end(self):
        if self._end is None:
            # In order for 'end' to be calculated, 'self' must be iterated over
            # first. Normally this should happen on its own when we're
            # searching in a DFS manner, otherwise, we have to force it.
            for _ in self:
                pass
        return self._end

    @end.setter
    def end(self, value):
        self._end = value
