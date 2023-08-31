from __future__ import absolute_import

import re
from collections import OrderedDict, namedtuple

import six
import yaml
from yaml.constructor import ConstructorError

from openformats.exceptions import ParseError
from openformats.utils.compat import ensure_unicode

from .constants import YAML_BINARY_ID, YAML_STRING_ID
from .yaml_representee_classes import (BlockList, BlockStyleOrderedDict,
                                       FlowList, FlowStyleOrderedDict,
                                       double_quoted_unicode, folded_unicode,
                                       literal_unicode, plain_unicode,
                                       single_quoted_unicode)
from .yaml_representers import (block_list_representer,
                                block_style_ordered_dict_representer,
                                double_quoted_unicode_representer,
                                flow_list_representer,
                                flow_style_ordered_dict_representer,
                                folded_unicode_representer,
                                literal_unicode_representer,
                                ordered_dict_representer,
                                single_quoted_unicode_representer,
                                unicode_representer)

yaml.add_representer(six.text_type, unicode_representer)
yaml.add_representer(plain_unicode, unicode_representer)
yaml.add_representer(six.binary_type, unicode_representer)
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


Node = namedtuple("Node", ['value', 'start', 'end', 'style', 'tag'])


class TxYamlLoader(yaml.SafeLoader):
    """
    Custom YAML Loader for Tx
    """

    def __init__(self, *args, **kwargs):
        super(TxYamlLoader, self).__init__(*args, **kwargs)
        self.stream = args[0]
        self.post_block_comment_pattern = re.compile(
            ensure_unicode(r'(?:#.*\r?\n\s*)+$')
        )

    def compose_node(self, parent, index):
        """ Override parent compose_node method to ignore aliases """
        if self.check_event(yaml.events.AliasEvent):
            event = self.get_event()
            # the important thing is the value of the ScalarNode is an empty
            # string so that it is not parsed into a string
            # see https://github.com/yaml/pyyaml/blob/b6cbfeec35e019734263a8f4e6a3340e94fe0a4f/lib/yaml/composer.py#L64  # noqa
            # for the original behavior
            return yaml.nodes.ScalarNode(
                YAML_STRING_ID, u'', event.start_mark, event.end_mark
            )
        return super(TxYamlLoader, self).compose_node(parent, index)

    def compose_mapping_node(self, anchor):
        """
        Override mapping node composition in order to move
        start mark from anchor to first key.

        Copied for https://github.com/yaml/pyyaml/blob/master/lib/yaml/composer.py  # noqa
        """
        if anchor is None:
            return super(TxYamlLoader, self).compose_mapping_node(anchor)
        else:
            start_event = self.get_event()
            tag = start_event.tag
            if tag is None or tag == '!':
                tag = self.resolve(
                    yaml.MappingNode, None, start_event.implicit
                )
            node = yaml.MappingNode(tag, [],
                    start_event.start_mark, None,
                    flow_style=start_event.flow_style)
            if anchor is not None:
                self.anchors[anchor] = node

            index = -1
            start_mark = start_event.start_mark
            while not self.check_event(yaml.events.MappingEndEvent):
                item_key = self.compose_node(node, None)
                key_start_mark = item_key.start_mark

                if index == -1 or key_start_mark.index < index :
                    index = key_start_mark.index
                    start_mark = key_start_mark

                item_value = self.compose_node(node, item_key)
                node.value.append((item_key, item_value))

            end_event = self.get_event()
            node.end_mark = end_event.end_mark
            node.start_mark = start_mark
            return node

    def compose_scalar_node(self, anchor):
        """
            Override parent compose_scalar_node method to maintain
            the anchor label
        """
        if anchor is None:
            return super(TxYamlLoader, self).compose_scalar_node(anchor)
        else:
            node = super(TxYamlLoader, self).compose_scalar_node(anchor)
            if node.tag == u'tag:yaml.org,2002:null':
                # 'key: &anchor' should be interpreted as 'key:', ie the value
                # should be ignored
                return node
            anchor_value = self.stream[
                node.start_mark.index:node.end_mark.index
            ].split(' ', 1)[1]
            leading_spaces = len(anchor_value) - len(anchor_value.lstrip(' '))

            node.start_mark.index = node.end_mark.index - len(anchor_value) \
                + leading_spaces
            return node

    def _is_custom_tag(self, tag):
        """
        Check whether a value is tagged with a custom type.

        Detect custom tags, like:
            `foo: !bar test`
            `foo: !xml "<bar>Bar</bar>"`
        Built-in types, indicated by a `!!` prefix, will not be matched. We
        can't preserve the information whether a built-in tag like `!!str` was
        used for a value since the PyYAML library will tag such entries with
        the built-in identifier. For example `tag:yaml.org,2002:str`, not
        `!!str`.
        """
        return tag.startswith('!') and not tag.startswith('!!')

    def construct_mapping(self, node, deep=True):
        """
        Override `yaml.SafeLoader.construct_mapping` to return for each item
        of the mapping a tuple of the form `(key, (value, start, end, style,
        tag))` instead of the default which is `(key, value)`.
        :raise ParseError: if node is not a MappingNode
            or duplicate keys are found.
        """
        if not isinstance(node, yaml.MappingNode):
            raise ParseError(
                "Expected a mapping node, but found {}".format(node.id),
            )
        pairs = []
        for key_node, value_node in node.value:
            # don't process binary values
            if value_node.tag == YAML_BINARY_ID:
                continue
            try:
                key = self.construct_object(key_node, deep=deep)
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError as e:
                print("During parsing YAML file: {}".format(six.text_type(e)))
                continue

            # raise ConstructorError in case of invalid key
            try:
                hash(key)
            except TypeError as e:
                print("Error while constructing a mapping, found unacceptable"
                      " key ({})".format(six.text_type(e)))
                continue

            if not(isinstance(value, six.text_type) or
                   isinstance(value, six.binary_type) or
                   isinstance(value, list) or
                   isinstance(value, dict)):
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
                    start = (start -
                             (value_node.start_mark.column -
                              key_node.start_mark.column))

                    # re calculate end position taking into account
                    # comments after a block node (seq or mapping)
                    end = self._calculate_block_end_pos(start, end)
            elif (isinstance(value, six.binary_type) or
                  isinstance(value, six.text_type)):
                style = value_node.style

            # Setup the node's tag
            tag = None
            if (
                hasattr(value_node, 'tag')
                and self._is_custom_tag(value_node.tag)
            ):
                tag = six.text_type(value_node.tag)

            value = Node(value, start, end, style, tag)
            pairs.append((key, value))

        # If there are duplicate keys, throw an exception
        pair_keys = [pair[0] for pair in pairs]
        seen = set()
        duplicates = set()
        seen_add = seen.add
        duplicate_add = duplicates.add
        for x in pair_keys:
            if x not in seen:
                seen_add(x)
            else:
                duplicate_add(x)

        if len(duplicates):
            duplicates_list = list(duplicates)
            error_duplicate_keys = ', '.join(key for key in duplicates_list)
            raise ParseError(
                "Duplicate keys found ({})".format(error_duplicate_keys)
            )

        return pairs

    def construct_sequence(self, node, deep=True):
        """
        Override `yaml.SafeLoader.construct_sequence` to return a `Node` tuple
        instead of the default which is `value`.
        """
        if not isinstance(node, yaml.SequenceNode):
            raise ParseError(
                "Expected a mapping node, but found {}".format(node.id)
            )
        values = []

        for value_node in node.value:
            # don't process binary values
            if value_node.tag == YAML_BINARY_ID:
                continue
            try:
                value = self.construct_object(value_node, deep=deep)
            except ConstructorError as e:
                print("During parsing YAML file: {}".format(six.text_type(e)))
                continue
            if not(isinstance(value, six.text_type) or
                   isinstance(value, six.binary_type) or
                   isinstance(value, list) or
                   isinstance(value, dict)):
                continue
            start = value_node.start_mark.index
            end = value_node.end_mark.index
            if isinstance(value, (dict, list)):
                if value_node.flow_style:
                    style = 'flow'
                else:
                    style = 'block'
                values.append(Node(value, start, end, style, None))
            else:
                style = value_node.style
                values.append(Node(value, start, end, style, None))
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
            keys = list(map(self.handler.unescape_dots, keys))
            if se.pluralized:
                plural_rules = self.handler.get_plural_rules()
                for rule in plural_rules:
                    if rule != plural_rules[0]:
                        keys.pop()
                    keys.append(self.handler.get_rule_string(rule))
                    self._insert_translation_in_dict(
                        yaml_dict, keys, flags, se.string.get(rule), tag=None,
                    )
            else:
                self._insert_translation_in_dict(
                    yaml_dict, keys, flags, se.string, tag=se.context,
                )
        return yaml_dict

    def _get_styled_string(self, translation_string, style, tag=None):
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
            obj = literal_unicode(obj, tag=tag)
        elif style == '>':
            obj = folded_unicode(obj, tag=tag)
        elif style == '"':
            obj = double_quoted_unicode(obj, tag=tag)
        elif style == "'":
            obj = single_quoted_unicode(obj, tag=tag)
        elif tag:
            obj = plain_unicode(obj, tag=tag)
        return obj

    def _insert_translation_in_dict(self, parent_dict, keys, styles,
                                    translation_string, tag=None):
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

            # and yaml.dump would produce the following
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
            yaml_dict[key] = self._get_styled_string(entry, styles[-1],
                                                     tag=tag)
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
