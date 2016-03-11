class DumbJson(object):
    def __init__(self, source, start=0):
        self.source = source
        starting_symbol, self.start = self._find_next('{[', start)
        if starting_symbol == '{':
            self.type = dict
        elif starting_symbol == '[':
            self.type = list

    def wrong__iter__(self):
        # the '_p' suffix means "position"
        opening_bracket, opening_bracket_p = self._find_next('{[')
        if opening_bracket == '{':
            while True:
                # lets find our key
                _, start_key_quote_p = self._find_next('"',
                                                       opening_bracket_p + 1)
                key_p = start_key_quote_p + 1
                _, end_key_quote_p = self._find_next('"', key_p + 1)
                key = self.source[key_p:end_key_quote_p]
                _, colon_p = self._find_next(':', end_key_quote_p + 1)
                start_value, start_value_p = self._find_next('"{[',
                                                             colon_p + 1)
                if start_value == '"':
                    # We found a string!
                    _, start_value_quote_p = self._find_next('"',
                                                             start_value_p + 1)
                    value_p = start_value_p + 1
                    _, end_value_quote_p = self._find_next('"', value_p)
                    value = self.source[value_p:end_value_quote_p]
                    yield key, key_p, value, value_p
                    next_symbol, next_symbol_p = self._find_next(
                        ',}', end_value_quote_p + 1,
                    )
                    if next_symbol == ',':
                        opening_bracket_p = next_symbol_p
                        continue
                    elif next_symbol == '}':
                        break
                elif start_value in ('{', '['):
                    opening_bracket_p = start_value_p
                    continue
        elif opening_bracket == '[':
            while True:
                # lets find our item
                start_item_quote, start_item_quote_p = self._find_next(
                    '"{[', opening_bracket_p + 1,
                )
                if start_item_quote == '"':
                    item_p = start_item_quote_p + 1
                    _, end_item_quote_p = self._find_next('"', item_p)
                    item = self.source[item_p:end_item_quote_p]
                    yield item, item_p
                    next_symbol, next_symbol_p = self._find_next(
                        ',]', end_item_quote_p + 1,
                    )
                    if next_symbol == ',':
                        opening_bracket_p = next_symbol_p + 1
                        continue
                    elif next_symbol == ']':
                        break
                elif start_item_quote in ('{', '['):
                    opening_bracket_p = next_symbol_p
                    continue

    def __iter__(self):
        if self.type == dict:
            for what in self._iter_dict():
                yield what
        elif self.type == list:
            for what in self._iter_list():
                yield what

    def _iter_dict(self):
        start = self.start + 1
        while True:
            # Lets find our key
            _, start_key_quote_p = self._find_next('"', start)
            key_p = start_key_quote_p + 1
            _, end_key_quote_p = self._find_next('"', key_p)
            key = self.source[key_p:end_key_quote_p]
            _, colon_p = self._find_next(':', end_key_quote_p + 1)
            value_start, value_start_p = self._find_next('"{[', colon_p + 1)
            if value_start == '"':
                # We found a string!
                value_p = value_start_p + 1
                _, value_end_quote_p = self._find_next('"', value_p)
                value = self.source[value_p:value_end_quote_p]
                yield key, key_p, value, value_p
                next_p = value_end_quote_p + 1
            elif value_start in ('{', '['):
                # We found an embedded, lets return an instance of ourselves
                embedded = DumbJson(self.source, value_start_p)
                yield key, key_p, embedded, value_start_p
                next_p = embedded.end + 1
            next_symbol, next_symbol_p = self._find_next(',}', next_p)
            if next_symbol == ',':
                start = next_symbol_p + 1
            elif next_symbol == '}':
                self.end = next_symbol_p
                break

    def _iter_list(self):
        start = self.start + 1
        while True:
            # Lets find our items
            start_item_quote, start_item_quote_p = self._find_next('"{[',
                                                                   start)
            if start_item_quote == '"':
                # We found a string!
                item_p = start_item_quote_p + 1
                _, end_item_quote_p = self._find_next('"', item_p)
                item = self.source[item_p:end_item_quote_p]
                yield item, item_p
                next_p = end_item_quote_p + 1
            elif start_item_quote in ('{', '['):
                # We found an embedded, lets return an instance of ourselves
                embedded = DumbJson(self.source, start_item_quote_p)
                yield embedded, start_item_quote_p
                next_p = embedded.end + 1
            next_symbol, next_symbol_p = self._find_next(',]', next_p)
            if next_symbol == ',':
                start = next_symbol_p + 1
            elif next_symbol == ']':
                self.end = next_symbol_p
                break

    def _find_next(self, symbols, start=0):
        symbols = {s for s in symbols}
        for ptr in xrange(start, len(self.source)):
            candidate = self.source[ptr]
            if candidate in symbols:
                if (candidate in {'{', '[', '"', ','} and ptr > 0 and
                        self.source[ptr - 1] == '\\'):
                    continue
                return candidate, ptr
        return None, None
