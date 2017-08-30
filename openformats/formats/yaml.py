from __future__ import absolute_import

import yaml
import re
import copy

from yaml.constructor import ConstructorError

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import ParseError


class YamlHandler(Handler):

    def _load_yaml(self, content, loader):
        """
        Loads a YAML stream and returns a dictionary
        representation for YAML data

        Args:
            content: A string, YAML content
            loader: Yaml Loader class or None

        Returns:
            A dictionary
        """
        try:
            return yaml.load(content, Loader=loader)
        except yaml.scanner.ScannerError as e:
            raise ParseError(unicode(e))

    def _parse_leaf_node(self, yaml_dict, parent_key, key, style=[]):
        """Parse a leaf node in yaml_dict.
        Args:
            yaml_dict: A dictionary
            parent_key: A string of keys concatenated by '.' to
                reach this node
            key: A string for the current key of yaml_dict
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        value = yaml_dict[0]
        start = yaml_dict[1]
        end = yaml_dict[2]
        style.append(yaml_dict[3] or '')
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

    def _get_key_for_node(self, key, parent_key):
        """
        Get key string for the current node.

        Args:
            key: A string, current key for the node
            parent_key: A string, containing all the keys
                (traversed before reaching the current key node)
                separated by '.'

        Returns:
            A string similar to parent_key with key appended to it.
        """
        if not isinstance(key, basestring):
            # Int keys are stored in < and > around it, so it can be reverted
            # on int again on compiling.
            key = str('<%s>' % key)
        if '.' in key:
            key = self.unescape_dots(key)
        if parent_key == '':
            parent_key += key
        else:
            parent_key += '.' + key
        return parent_key

    def parse_dict(self, yaml_dict, parent_key, parsed_data,
                   context="", parent_style=[]):
        """
        Parse data returned by YAML loader and also handle plural
        data if available
        Args:
            yaml_dict: A dictionary
            parent_key: A string of keys concatenated by '.' to
                reach this node,
            parsed_data: A list, containing the already parsed data
            context: A string
            parent_style: A list of YAML node styles for each parent node.

        Returns:
            A list of dictionaries, where each dictionary maps a node
            key to its value
        """
        if isinstance(yaml_dict, dict):
            for key, val in yaml_dict.items():
                node_key = self._get_key_for_node(key, parent_key)
                style = copy.copy(parent_style)
                if isinstance(val[0], (dict, list)):
                    # style.append(val.get('style', ''))
                    parsed_data = self.parse_dict(
                        val[0], node_key, parsed_data, context,
                        parent_style=copy.copy(style or []))
                else:
                    parsed_data.append(
                        self._parse_leaf_node(
                            val, node_key, key, style=copy.copy(parent_style or
                                                                [])
                        )
                    )
        elif (isinstance(yaml_dict, list)):
            # If a list of dicts, add each dict element as a entry
            # using the position (index) of it as parent key using
            # brackets around it. I.e.: 'foo.[0].bar'.
            for i, e in enumerate(yaml_dict):
                p_key = parent_key + '.[%s]' % (i)
                if isinstance(e, (dict, list)):
                    parsed_data = self.parse_dict(
                        e, p_key, parsed_data, context,
                        parent_style=copy.copy(parent_style or []))
                else:
                    parsed_data.append(
                        self._parse_leaf_node(
                            e, p_key, i, style=copy.copy(parent_style or [])
                        )
                    )
        else:
            parsed_data.append(
                self._parse_leaf_node(
                    yaml_dict, node_key, key,
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
        yaml_dict = self._load_yaml(content, loader=TxYamlLoader)
        parsed_data = self.parse_dict(
            yaml_dict, '', [], context)
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
            style = ''
            if isinstance(value, (dict, list)):
                values.append(value)
            else:
                values.append((value, start, end, style))
        return values
