from __future__ import absolute_import

import yaml
import re
from collections import OrderedDict

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


class TxYamlLoader(yaml.SafeLoader):
    """
    Custom YAML Loader for Tx
    """
    def __init__(self, *args, **kwargs):
        super(TxYamlLoader, self).__init__(*args, **kwargs)
        self.stream = args[0]
        self.post_block_comment_pattern = re.compile(
            r'(?:#.*\r?\n\s*)+$')

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

    def construct_mapping(self, node, deep=True):
        if not isinstance(node, yaml.MappingNode):
            raise ParseError(
                "Expected a mapping node, but found %s" % node.id,
            )
        pairs = []
        for key_node, value_node in node.value:
            try:
                key = self.construct_object(key_node, deep=deep)
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError, e:
                print("During parsing YAML file: %s" % unicode(e))
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

            value = (value, start, end, style)
            pairs.append((key, value))
        return pairs

    def construct_sequence(self, node, deep=True):
        if not isinstance(node, yaml.SequenceNode):
            raise ParseError(
                "Expected a mapping node, but found %s" % node.id,
            )
        values = []

        for value_node in node.value:
            try:
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError, e:
                print("During parsing YAML file: %s" % unicode(e))
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
                values.append((value, start, end, style))
            else:
                style = value_node.style
                values.append((value, start, end, style))
        return values


class YamlGenerator(object):
    """
    Generate YAML content for a resource translation
    """

    def __init__(self, handler):
        self.handler = handler

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

    def _insert_translation_in_dict(self, parent_dict, keys, openstring,
                                    translation_string):
        styles = openstring.flags.split(':')
        yaml_dict = parent_dict
        entry = translation_string
        if len(keys) == 1:
            key = keys[0]
            # Check whether the key should be turned into an int value.
            if key.startswith('<') and key.endswith('>'):
                try:
                    key = int(key[1:-1])
                except ValueError:
                    pass
            yaml_dict[key] = self._get_styled_string(entry, styles[-1])
            return

        for i, key in enumerate(keys[:-1]):
            is_last = i == (len(keys) - 2)
            next_key = keys[i+1]
            is_list, next_is_list = False, False

            # Check whether the key should be turned into an int value.
            if key.startswith('<') and key.endswith('>'):
                try:
                    key = int(key[1:-1])
                except ValueError:
                    pass
            try:
                next_key = int(next_key[1:-1])
                next_is_list = True
            except ValueError:
                pass
            try:
                key = int(key[1:-1])
                index = key
                is_list = True
            except ValueError:
                pass

            if not is_list:
                if key in yaml_dict:
                    yaml_dict = yaml_dict.get(key)
                else:
                    if next_is_list:
                        yaml_dict[key] = BlockList()
                        if is_last and styles[i] == 'flow':
                            yaml_dict[key] = FlowList()
                    else:
                        yaml_dict[key] = OrderedDict()
                        if is_last and styles[i] == 'flow':
                            yaml_dict[key] = FlowStyleOrderedDict()
                        if is_last and styles[i] == 'block':
                            yaml_dict[key] = BlockStyleOrderedDict()
                    yaml_dict = yaml_dict[key]
            else:
                if index < len(yaml_dict):
                    yaml_dict = yaml_dict[index]
                else:
                    if next_is_list:
                        yaml_dict.append(BlockList())
                    else:
                        yaml_dict.append(OrderedDict())
                    yaml_dict = yaml_dict[index]
            if is_last:
                if next_is_list:
                    yaml_dict.append(self._get_styled_string(entry,
                                                             styles[-1]))
                else:
                    yaml_dict[next_key] = self._get_styled_string(entry,
                                                                  styles[-1])

    def _generate_yaml_dict(self, stringset):
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
            keys = map(self.handler.escape_dots, keys)
            if se.pluralized:
                plural_rules = self.handler.get_plural_rules()
                for rule in plural_rules:
                    if rule != plural_rules[0]:
                        keys.pop()
                    keys.append(self.get_rule_string(rule))
                    self._insert_translation_in_dict(
                        yaml_dict, keys, se, se.string.get(rule)
                    )
            else:
                self._insert_translation_in_dict(
                    yaml_dict, keys, se, se.string
                )
        return yaml_dict


class TxYamlDumper(yaml.Dumper):
    """
    Custom YAML dumper for Tx
    """
    def increase_indent(self, flow=False, indentless=False):
        return super(TxYamlDumper, self).increase_indent(flow, False)
