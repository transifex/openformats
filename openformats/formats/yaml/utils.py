from __future__ import absolute_import

import yaml
import re
from collections import OrderedDict, namedtuple

from yaml.constructor import ConstructorError

from openformats.exceptions import ParseError

from .yaml_representee_classes import (BlockList, FlowList, literal_unicode,
                                       folded_unicode, double_quoted_unicode,
                                       single_quoted_unicode,
                                       BlockStyleOrderedDict,
                                       FlowStyleOrderedDict)
from .yaml_representers import (unicode_representer,
                                folded_unicode_representer,
                                literal_unicode_representer,
                                double_quoted_unicode_representer,
                                single_quoted_unicode_representer,
                                block_list_representer, flow_list_representer,
                                ordered_dict_representer,
                                block_style_ordered_dict_representer,
                                flow_style_ordered_dict_representer)


yaml.add_representer(unicode, unicode_representer)
yaml.add_representer(str, unicode_representer)
yaml.add_representer(folded_unicode, folded_unicode_representer)
yaml.add_representer(literal_unicode, literal_unicode_representer)
yaml.add_representer(double_quoted_unicode,
                     double_quoted_unicode_representer)
yaml.add_representer(single_quoted_unicode,
                     single_quoted_unicode_representer)
yaml.add_representer(BlockList, block_list_representer)
yaml.add_representer(FlowList, flow_list_representer)
yaml.add_representer(OrderedDict, ordered_dict_representer)
yaml.add_representer(BlockStyleOrderedDict,
                     block_style_ordered_dict_representer)
yaml.add_representer(FlowStyleOrderedDict,
                     flow_style_ordered_dict_representer)


Node = namedtuple("Node", ['value', 'start', 'end', 'style'])


class TxYamlLoader(yaml.SafeLoader):
    """
    Custom YAML Loader for Tx
    """
    def __init__(self, *args, **kwargs):
        super(TxYamlLoader, self).__init__(*args, **kwargs)
        self.stream = args[0]
        self.post_block_comment_pattern = re.compile(r'(?:#.*\r?\n\s*)+$')

    def construct_mapping(self, node, deep=True):
        """
        Override `yaml.SafeLoader.construct_mapping` to return for each item
        of the mapping a tuple of the form `(key, (value, start, end, style))`
        instead of the default which is `(key, value)`.
        """
        if not isinstance(node, yaml.MappingNode):
            raise ParseError(
                "Expected a mapping node, but found {}".format(node.id),
            )
        pairs = []
        for key_node, value_node in node.value:
            # don't process binary values
            if value_node.tag == 'tag:yaml.org,2002:binary':
                continue
            try:
                key = self.construct_object(key_node, deep=deep)
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError as e:
                print("During parsing YAML file: {}".format(unicode(e)))
                continue

            # raise ConstructorError in case of invalid key
            try:
                hash(key)
            except TypeError as e:
                print("Error while constructing a mapping, found unacceptable"
                      " key (%s)".format(unicode(e)))
                continue

            if not(isinstance(value, unicode) or isinstance(value, str) or
                    isinstance(value, list) or isinstance(value, dict)):
                continue
            start = value_node.start_mark.index
            end = value_node.end_mark.index
            style = ''

            # take into account key strings that translate into
            # boolean objects.
            if isinstance(key, bool):
                key = self.stream[key_node.start_mark.index:
                                  key_node.end_mark.index]

            if isinstance(value, list) or isinstance(value, dict):
                if value_node.flow_style:
                    style = 'flow'
                else:
                    style = 'block'
                    start = (start - (value_node.start_mark.column -
                             key_node.start_mark.column))
                    # re calculate end position taking into account
                    # comments after a block node (seq or mapping)
                    end = self._calculate_block_end_pos(start, end)

            elif isinstance(value, str) or isinstance(value, unicode):
                style = value_node.style

            value = Node(value, start, end, style)
            pairs.append((key, value))
        return pairs

    def construct_sequence(self, node, deep=True):
        """
        Override `yaml.SafeLoader.construct_sequence` to return for each
        element of the sequence `(value, start, end, style)` instead of the
        default which is `value`.
        """
        if not isinstance(node, yaml.SequenceNode):
            raise ParseError(
                "Expected a mapping node, but found {}".format(node.id)
            )
        values = []

        for value_node in node.value:
            # don't process binary values
            if value_node.tag == 'tag:yaml.org,2002:binary':
                continue
            try:
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError as e:
                print("During parsing YAML file: {}".format(unicode(e)))
                continue
            if not(isinstance(value, unicode) or isinstance(value, str) or
                    isinstance(value, list) or isinstance(value, dict)):
                continue
            start = value_node.start_mark.index
            end = value_node.end_mark.index
            if isinstance(value, (dict, list)):
                if value_node.flow_style:
                    style = 'flow'
                else:
                    style = 'block'
                values.append(Node(value, start, end, style))
            else:
                style = value_node.style
                values.append(Node(value, start, end, style))
        return values

    def _calculate_block_end_pos(self, start, end):
        """
        This recalculates the end position of a block seq
        in self.stream. This is done to take into account
        comments between a block sequence or mapping node
        and the next node.

        Args:
            start: An integer, start position of block sequence
                   in self.stream
            end: An integer, end position of block sequence in
                self.stream.

        Returns:
            An integer for the new end position.
        """
        content = self.stream[start:end]
        m = self.post_block_comment_pattern.search(content)
        if m:
            end = start + m.start()
        return end


class YamlGenerator(object):
    """
    Generate YAML content for a resource translation.

    Use keys and styles of each string in the stringset to recreate
    the original structure of the YAML file.
        - keys refer to `string.key.split('.')`
        - styles refer to `string.flags.split(':')`

    Used when we want to compile the translation file without using the
    resource template.
    """

    def __init__(self, handler):
        self.handler = handler

    def generate_yaml_dict(self, stringset):
        """
        Generate a dictionary to be serialized to YAML.

        Args:
            stringset: The OpenString stringset of the resource

        Returns:
            An YAML serializable OrderedDict instance.
        """
        yaml_dict = OrderedDict()
        for se in stringset:
            keys = se.key.split('.')
            flags = se.flags.split(':')
            keys = map(self.handler.unescape_dots, keys)
            if se.pluralized:
                plural_rules = self.handler.get_plural_rules()
                for rule in plural_rules:
                    if rule != plural_rules[0]:
                        keys.pop()
                    keys.append(self.handler.get_rule_string(rule))
                    self._insert_translation_in_dict(
                        yaml_dict, keys, flags, se.string.get(rule)
                    )
            else:
                self._insert_translation_in_dict(
                    yaml_dict, keys, flags, se.string
                )
        return yaml_dict

    def _get_styled_string(self, translation_string, style):
        """
        Wrap a translation string so that it can be serialized
        to YAML with proper style.

        Args:
            translation_string: A translation string
            style: Style for the translation string

        Returns:
            A subclass of Unicode, either
            folded_unicode, literal_unicode, single_quoted_unicode,
            or double_quoted_unicode.
        """
        obj = translation_string
        if style == '|':
            obj = literal_unicode(obj)
        elif style == '>':
            obj = folded_unicode(obj)
        elif style == '"':
            obj = double_quoted_unicode(obj)
        elif style == "'":
            obj = single_quoted_unicode(obj)
        return obj

    def _insert_translation_in_dict(self, parent_dict, keys, styles,
                                    translation_string):
        """ Given a set of keys and a set of styles generate a YAML
        serializable dictionary with each nested element cast to the
        right YAML representee class.

        Args:
            keys: a list produced by the source string key split on `.`
            parent_dict: OrderedDict we want to update
            styles: A list of flags denoting the string's style in the
                original YAML file. Valid flags are:
                ["block", "flow", "'", "\"", ">", "|", ""]
            translation_string: the translation string

        Example:
            ```
            keys = ["one", "two", "[0]"]
            flags = "block:block:block:'".split(':')
            translation_string = "test"
            result = OrderedDict()

            _insert_translation_in_dict(result, keys, flags,
                                        translation_string)
            # produced result
            OrderedDict([
                (u'one', OrderedDict([
                    (u'two', BlockList([
                        single_quoted_unicode(u'test')
                    ]))
                ]))
            ])

            # re-calling _insert_translation_in_dict with second set of keys
            # the `result` as `parent_dict` would update the same dictionary
            keys = ["one", "two", "[1]"]
            flags = "block:block:block:\"".split(':')
            translation_string = "test 2"

            _insert_translation_in_dict(result, keys, flags,
                                        translation_string)
            # produced result
            OrderedDict([
                (u'one', OrderedDict([
                    (u'two', BlockList([
                        single_quoted_unicode(u'test')
                        double_quoted_unicode(u'test 2')
                    ]))
                ]))
            ])

            # and yaml.dump whould produce the following
            yaml.dump(result, Dumper=TxYamlDumper, allow_unicode=True)
            one:
              two:
                - 'test'
                - "test 2"
            ```
        """
        yaml_dict = parent_dict
        entry = translation_string
        if len(keys) == 1:
            key = self._parse_int_key(keys[0])
            yaml_dict[key] = self._get_styled_string(entry, styles[-1])
            return

        for i, key in enumerate(keys[:-1]):
            is_last = i == (len(keys) - 2)
            next_key = keys[i+1]

            key = self._parse_int_key(key)
            key, is_list = self._parse_list_index_key(key)
            next_key, next_is_list = self._parse_list_index_key(next_key)

            if is_list:
                index = key

            if not is_list:
                if key in yaml_dict:
                    yaml_dict = yaml_dict.get(key)
                else:
                    if next_is_list:
                        yaml_dict[key] = self._create_list_node(styles[i])
                    else:
                        yaml_dict[key] = self._create_dict_node(styles[i])
                    yaml_dict = yaml_dict[key]
            else:
                if index < len(yaml_dict):
                    yaml_dict = yaml_dict[index]
                else:
                    if next_is_list:
                        yaml_dict.append(self._create_list_node(styles[i]))
                    else:
                        yaml_dict.append(self._create_dict_node(styles[i]))
                    yaml_dict = yaml_dict[index]
            if is_last:
                if next_is_list:
                    yaml_dict.append(self._get_styled_string(entry,
                                                             styles[-1]))
                else:
                    yaml_dict[next_key] = self._get_styled_string(entry,
                                                                  styles[-1])

    def _create_list_node(self, style):
        if style == 'block':
            return BlockList()
        elif style == 'flow':
            return FlowList()

    def _create_dict_node(self, style=None):
        if style == 'block':
            return BlockStyleOrderedDict()
        elif style == 'flow':
            return FlowStyleOrderedDict()

        return OrderedDict()

    def _parse_int_key(self, key):
        """
        Check whether the key should be turned into an int value.

        Returns:
            The key cast to an integer if needed
        """
        if key.startswith('<') and key.endswith('>'):
            try:
                key = int(key[1:-1])
            except ValueError:
                pass
        return key

    def _parse_list_index_key(self, key):
        """
        Check whether the key is in fact the index of a list.

        Returns:
            key: The key cast to an integer if needed
            is_list: A Boolean indicating if key is indeed a list index
        """
        is_list = False
        if key.startswith('[') and key.endswith(']'):
            try:
                key = int(key[1:-1])
                is_list = True
            except ValueError:
                pass
        return (key, is_list)


class TxYamlDumper(yaml.Dumper):
    """
    Custom YAML dumper for Tx
    """
    def increase_indent(self, flow=False, indentless=False):
        return super(TxYamlDumper, self).increase_indent(flow, False)
