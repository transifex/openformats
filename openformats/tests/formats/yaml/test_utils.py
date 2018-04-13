import unittest
from mock import MagicMock
from collections import OrderedDict

from openformats.formats.yaml.utils import YamlGenerator

from openformats.formats.yaml.yaml_representee_classes import (
    BlockList, FlowList, literal_unicode, folded_unicode,
    double_quoted_unicode, single_quoted_unicode,
    BlockStyleOrderedDict, FlowStyleOrderedDict
)


class YamlGeneratorTestCase(unittest.TestCase):

    def test_insert_translation_in_dict_empty_parent(self):
        keys = ["one", "two", "[0]"]
        flags = "block:block:'".split(':')
        translation_string = "test"
        result = OrderedDict()

        YamlGenerator(MagicMock())._insert_translation_in_dict(
            result, keys, flags, translation_string
        )
        # produced result
        # OrderedDict([
        #     (u'one', OrderedDict([
        #         (u'two', BlockList([
        #             single_quoted_unicode(u'test')
        #         ]))
        #     ]))
        # ])
        self.assertListEqual(result.keys(), ['one'])
        self.assertIsInstance(result['one'], OrderedDict)
        self.assertIsInstance(result['one']['two'], BlockList)
        self.assertIsInstance(result['one']['two'][0], single_quoted_unicode)

    def test_insert_translation_in_dict_non_empty_parent(self):
        result = OrderedDict()
        result['one'] = OrderedDict()
        result['one']['three'] = 'a string'
        keys = ["one", "two", "[0]"]

        flags = "block:block:'".split(':')
        translation_string = "test"

        YamlGenerator(MagicMock())._insert_translation_in_dict(
            result, keys, flags, translation_string
        )
        # produced result
        # OrderedDict([
        #     (u'one', OrderedDict([
        #         (u'three', 'a string'),
        #         (u'two', BlockList([
        #             single_quoted_unicode(u'test')
        #         ]))
        #     ]))
        # ])
        self.assertListEqual(result.keys(), ['one'])
        self.assertListEqual(result['one'].keys(), ['three', 'two'])
        self.assertIsInstance(result['one']['two'], BlockList)
        self.assertIsInstance(result['one']['two'][0], single_quoted_unicode)

    def test_insert_translation_in_dict_flow_list(self):
        result = OrderedDict()
        keys = ["one", "two", "[0]"]
        flags = "block:flow:\"".split(':')
        translation_string = "test"

        YamlGenerator(MagicMock())._insert_translation_in_dict(
            result, keys, flags, translation_string
        )
        # produced result
        # OrderedDict([
        #     (u'one', OrderedDict([
        #         (u'two', FlowList([
        #             double_quoted_unicode(u'test')
        #         ]))
        #     ]))
        # ])
        self.assertListEqual(result.keys(), ['one'])
        self.assertIsInstance(result['one'], OrderedDict)
        self.assertIsInstance(result['one']['two'], FlowList)
        self.assertIsInstance(result['one']['two'][0], double_quoted_unicode)

    def test_insert_translation_in_dict_flow_dict(self):
        result = OrderedDict()
        keys = ["one", "two"]
        flags = "flow:\"".split(':')
        translation_string = "test"

        YamlGenerator(MagicMock())._insert_translation_in_dict(
            result, keys, flags, translation_string
        )
        # produced result
        # OrderedDict([
        #     (u'one', FlowStyleOrderedDict([
        #         (u'two', double_quoted_unicode(u'test'))
        #     ]))
        # ])
        self.assertListEqual(result.keys(), ['one'])
        self.assertIsInstance(result['one'], FlowStyleOrderedDict)
        self.assertIsInstance(result['one']['two'], double_quoted_unicode)

    def test_insert_translation_in_dict_list_of_dicts(self):
        result = OrderedDict()
        keys = ["one", "[0]", "two"]
        flags = "block:flow:\"".split(':')
        translation_string = "test"

        YamlGenerator(MagicMock())._insert_translation_in_dict(
            result, keys, flags, translation_string
        )
        # produced result
        # OrderedDict([
        #     (u'one', BlockList([
        #         BlockStyledOrderedDict([
        #             (u'two', double_quoted_unicode(u'test'))
        #         ])
        #     ]))
        # ])
        self.assertListEqual(result.keys(), ['one'])
        self.assertIsInstance(result['one'], BlockList)
        self.assertIsInstance(result['one'][0], FlowStyleOrderedDict)
        self.assertIsInstance(result['one'][0]['two'], double_quoted_unicode)
