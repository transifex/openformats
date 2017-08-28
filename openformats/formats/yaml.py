from __future__ import absolute_import

import yaml
import re
import json
import copy

from yaml.constructor import ConstructorError

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import ParseError


class YamlHandler(Handler):

    def _load_yaml(self, content, loader):
        return yaml.load(content, Loader=loader)

    def _parse_leaf_node(self, yaml_dict, parent_key, key,
                         plural=False, style=[]):
        """Parse a leaf node in yaml_dict.
        Args:
            yaml_dict: A dictionary
            parent_key: A string of keys concatenated by '.' to
                reach this node
            key: A string for the current key of yaml_dict
            plural: A boolean, True if node is pluralized
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        if plural:
            value = {}
            for k in yaml_dict['value'].keys():
                value[k] = {}
                value[k]['value'] = yaml_dict['value'][k][0]
                value[k]['style'] = yaml_dict['value'][k][3]
            start = yaml_dict['start']
            end = yaml_dict['end']
        else:
            value = yaml_dict[key][0]
            start = yaml_dict[key][1]
            end = yaml_dict[key][2]
            style.append(yaml_dict[key][3] or '')
        return {
            'start': start,
            'end': end,
            'key': parent_key,
            'value': value,
            'style': ':'.join(style or [])
        }

    @staticmethod
    def escape_dots(k):
        return k.replace('<TX_DOT>', '.')

    @staticmethod
    def unescape_dots(k):
        return k.replace('.', '<TX_DOT>')

    def _get_key_for_node(self, key, parent_key, plural=False):
        """
        Get key string for the current node.

        Args:
            key: A string, current key for the node
            parent_key: A string, containing all the keys
                (traversed before reaching the current key node)
                separated by '.'
            plural: A boolean, True if node is pluralized

        Returns:
            A string similar to parent_key with key appended to it.
        """
        if not isinstance(key, basestring):
            # Int keys are stored in < and > around it, so it can be reverted
            # on int again on compiling.
            key = str('<%s>' % key)
        if '.' in key:
            key = self.unescape_dots(key)
        if not plural:
            if parent_key == '':
                parent_key += key
            else:
                parent_key += '.' + key
        return parent_key

    def parse_dict(self, yaml_dict, parent_key, parsed_data,
                   is_source, context="", parent_style=[]):
        """
        Parse data returned by YAML loader and also handle plural
        data if available
        Args:
            yaml_dict: A dictionary
            parent_key: A string of keys concatenated by '.' to
                reach this node,
            parsed_data: A list, containing the already parsed data
            is_source: A boolean, True if upload is in source language
            context: A string
            parent_style: A list of YAML node styles for each parent node.

        Returns:
            A list of dictionaries, where each dictionary maps a node
            key to its value
        """
        value = yaml_dict.get('value') or yaml_dict
        for key, val in value.items():
            node_key = self._get_key_for_node(key, parent_key)
            style = copy.copy(parent_style)
            if isinstance(val, dict):
                style.append(val.get('style', ''))
                parsed_data = self.parse_dict(val, node_key,
                    parsed_data, is_source, context,
                    parent_style=copy.copy(style or []))
            elif (isinstance(val[0], list) and val[0] and
                    isinstance(val[0][0], dict)):
                # If a list of dicts, add each dict element as a entry
                # using the position (index) of it as parent key using
                # brackets around it. I.e.: 'foo.[0].bar'.
                for i, e in enumerate(val[0]):
                    for k, v in e.items():
                        p_key = node_key + '.[%s].%s' % (i, k)
                        parsed_data.append(
                            self._parse_leaf_node(
                                e, p_key, k, style=copy.copy(parent_style or [])
                            )
                        )
            else:
                parsed_data.append(
                    self._parse_leaf_node(
                        value, node_key, key,
                        style=copy.copy(parent_style or [])
                    )
                )
        return parsed_data

    def _find_comment(self, content, start, end):
        lines = [
            line.strip()
            for line in content[start:end].split('\n')
            if line.strip() != ""
        ]
        lines.reverse()

        # remove non-comment line just before the string to be translated
        if lines and not lines[0].startswith('#'):
            del lines[0]

        returned_lines = []
        for line in lines:
            if not line.startswith('#'):
                break
            returned_lines.append(line[1:].strip())

        if returned_lines:
            returned_lines.reverse()
            return " ".join(returned_lines)
        else:
            return None

    def parse(self, content, **kwargs):
        template = ""
        context = ""
        stringset = []
        is_source = True
        trailing_dashes = content[-5:]
        content = content[:-5]
        yaml_dict = self._load_yaml(content, loader=TxYamlLoader)
        parsed_data = self.parse_dict(
            yaml_dict, '', [], is_source, context)
        parsed_data.sort()

        end = 0
        order = 0
        for node in parsed_data:
            start = node.get('start')
            end_ = node.get('end')
            key = node.get('key')
            value = node.get('value')
            style = node.get('style')
            comment = None
            if isinstance(value, dict) or value:
                string_object = OpenString(
                    key, value, context=context, flags=style, order=order,
                    comment=comment
                )
                stringset.append(string_object)
                order += 1
                template += (content[end:start] +
                             string_object.template_replacement)
            else:
                template += content[end:end_]
                end = end_
                continue
            comment = self._find_comment(content, end, start)
            end = end_

        template += content[end:]
        template += trailing_dashes
        return stringset, template


class TxYamlLoader(yaml.SafeLoader):
    """
    Custom YAML Loader for Tx
    """
    def __init__(self, *args, **kwargs):
        super(TxYamlLoader, self).__init__(*args, **kwargs)
        self.stream = args[0]
        self.post_block_comment_pattern = re.compile(
            r'(?:#.*\r?\n\s*)+$')

    def construct_yaml(self, node):
        value = self.construct_scalar(node)
        try:
            return value.encode('utf-8')
        except UnicodeEncodeError, e:
            print(
                'Unicode decode error in TxYamlLoader.construct_yaml: %s'
                % unicode(e)
            )
            return value
        except Exception, e:
            raise ParseError(
                "Unhandled exception in TxYamlLoader.construct_yaml(): %s"
                % unicode(e)
            )

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

            if not isinstance(value, dict):
                if (isinstance(value, list) and not
                        (value and isinstance(value[0], dict))):
                    value = json.dumps(value)
                value = (value, start, end, style)
            else:
                value = {'value': value, 'start': start,
                         'end': end, 'style': style}
            pairs.append((key, value))
        return pairs
