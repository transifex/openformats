import unittest

from openformats.utils.json import DumbJson


class DumbJsonTestCase(unittest.TestCase):
    # Dicts
    def test_simple_dict(self):
        self._test_dfs('{"a": "b"}', [("a", 2, "b", 7)])

    def test_simple_dict_with_two_items(self):
        self._test_dfs('{"a": "b", "c": "d"}',
                       [("a", 2, "b", 7), ("c", 12, "d", 17)])

    def test_empty_dict(self):
        self._test_dfs('{  }', [])

    def test_empty_dict_inbetween(self):
        self._test_dfs('["a", {  }, "b"]', [("a", 2), ([], 6), ("b", 13)])

    def test_dict_with_non_string_values(self):
        self._test_dfs('{"string": "Hello World", "True": true, '
                       '"False": false, "None": null, "Integer": 1234, '
                       '"Negative integer": -1234, "Float": 12.34, '
                       '"Negative float": -12.34, "E-notation": 12e34, '
                       '"Negative e-notation": 12e-34}',
                       [("string", 2, "Hello World", 12),
                        ("True", 27, True, 34),
                        ("False", 41, False, 49), ("None", 57, None, 64),
                        ("Integer", 71, 1234, 81),
                        ("Negative integer", 88, -1234, 107),
                        ("Float", 115, 12.34, 123),
                        ("Negative float", 131, -12.34, 148),
                        ("E-notation", 157, 12e34, 170),
                        ("Negative e-notation", 178, 12e-34, 200)])

    # Lists
    def test_simple_list(self):
        self._test_dfs('["a"]', [("a", 2)])

    def test_simple_list_with_two_items(self):
        self._test_dfs('["a", "b"]', [("a", 2), ("b", 7)])

    def test_empty_list(self):
        self._test_dfs('[  ]', [])

    def test_empty_list_inbetween(self):
        self._test_dfs('{"a": "b", "c": [  ], "d": "e"}',
                       [("a", 2, "b", 7), ("c", 12, [], 16),
                        ("d", 23, "e", 28)])

    def test_list_with_non_string_values(self):
        self._test_dfs('["Hello world", true, false, null, 1234, -1234, '
                       '12.34, -12.34, 12e34, 12e-34]',
                       [("Hello world", 2), (True, 16), (False, 22),
                        (None, 29), (1234, 35), (-1234, 41), (12.34, 48),
                        (-12.34, 55), (12e34, 63), (12e-34, 70)])

    # Nested
    def test_dict_within_dict(self):
        self._test_dfs('{"a": {"b": "c"}}', [("a", 2, [("b", 8, "c", 13)], 6)])

    def test_list_within_list(self):
        self._test_dfs('["a", ["b", "c"]]',
                       [("a", 2), ([("b", 8), ("c", 13)], 6)])

    def test_list_within_dict(self):
        self._test_dfs('{"a": ["b", "c"]}',
                       [("a", 2, [("b", 8), ("c", 13)], 6)])

    def test_dict_within_list(self):
        self._test_dfs('["a", {"b": "c"}]',
                       [("a", 2), ([("b", 8, "c", 13)], 6)])

    # Utils
    def _test_dfs(self, content, against):
        dumb_json = DumbJson(content)
        sample = self._dfs(dumb_json)
        self.assertEquals(sample, against)

    def _dfs(self, dumb_json):
        sample = []
        for row in dumb_json:
            if len(row) == 4:  # dict
                key, key_p, value, value_p = row
                if isinstance(value, DumbJson):
                    sample.append((key, key_p,
                                   self._dfs(value), value_p))
                else:
                    sample.append(row)
            elif len(row) == 2:  # list
                item, item_p = row
                if isinstance(item, DumbJson):
                    sample.append((self._dfs(item), item_p))
                else:
                    sample.append(row)
        return sample
