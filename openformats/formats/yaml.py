from __future__ import absolute_import

import yaml
import re
import copy

from yaml.constructor import ConstructorError

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import ParseError
from ..transcribers import Transcriber


class YamlHandler(Handler):
    name = "Yaml"
    extension = "yml"
    EXTRACTS_RAW = False

    BACKSLASH = u'\\'
    DOUBLE_QUOTES = u'"'
    NEWLINE = u'\n'
    COLON = u':'
    ASTERISK = u'*'
    AMPERSAND = u'&'
    DASH = u'-'
    HASHTAG = u'#'

    def _should_wrap_in_quotes(self, tr_string):
        return any([
            self.NEWLINE in tr_string[:-1],
            self.COLON in tr_string,
            self.HASHTAG in tr_string,
            tr_string.lstrip().startswith(self.ASTERISK),
            tr_string.lstrip().startswith(self.AMPERSAND),
            tr_string.lstrip().startswith(self.DASH),
        ])

    def _wrap_in_quotes(self, tr_string):
        if self._should_wrap_in_quotes(tr_string):
            # escape double quotes inside strings
            tr_string = tr_string.replace(
                self.DOUBLE_QUOTES,
                (self.BACKSLASH + self.DOUBLE_QUOTES)
            )
            # surround string with double quotes
            tr_string = (self.DOUBLE_QUOTES + tr_string +
                         self.DOUBLE_QUOTES)
        return tr_string

    def _compile_single(self, string):
        tr_string = self._wrap_in_quotes(string.string)
        # this is to ensure that if the style is literal or folded
        # http://www.yaml.org/spec/1.2/spec.html#id2795688
        # a new line always follows the string
        if (string.flags and string.flags in '|>' and
                tr_string[-1] != self.NEWLINE):
            tr_string = tr_string + self.NEWLINE
        return tr_string

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

    def _parse_leaf_node(self, yaml_data, parent_key, style=[],
                         pluralized=False):
        """Parse a leaf node in yaml_dict.
        Args:
            yaml_data: A tuple of the form (string, start, end, style)
            parent_key: A string of keys concatenated by '.' to
                reach this node
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        val = yaml_data[0]
        value = self.parse_pluralized_value(val) if pluralized else val
        start = yaml_data[1]
        end = yaml_data[2]
        style.append(yaml_data[3] or '')
        return {
            'start': start,
            'end': end,
            'key': parent_key,
            'value': value,
            'style': ':'.join(style or []),
            'pluralized': pluralized,
        }

    @staticmethod
    def unescape_dots(k):
        """ We use dots to construct the strings key, so we need to
        escape dots that are part of an actual YAML key """
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

    def parse_yaml_data(self, yaml_data, parent_key, parsed_data,
                        context="", parent_style=[]):
        """
        Parse data returned by YAML loader
        Args:
            yaml_data: The output of yaml.loads()
            parent_key: A string of keys concatenated by '.' to
                reach this node,
            parsed_data: A list, containing the already parsed data
            context: A string
            parent_style: A list of YAML node styles for each parent node.

        Returns:
            A list of dictionaries, where each dictionary maps a node
            key to its value
        """
        if isinstance(yaml_data, dict):
            for key, val in yaml_data.items():
                node_key = self._get_key_for_node(key, parent_key)
                style = copy.copy(parent_style)
                if isinstance(val[0], dict):
                    if self.is_pluralized(val[0]):
                        parsed_data.append(
                            self._parse_leaf_node(
                                val, node_key,
                                style=copy.copy(parent_style or []),
                                pluralized=True
                            )
                        )
                    else:
                        parsed_data = self.parse_yaml_data(
                            val[0], node_key, parsed_data, context,
                            parent_style=copy.copy(style or []))
                elif isinstance(val[0], list):
                    parsed_data = self.parse_yaml_data(
                        val[0], node_key, parsed_data, context,
                        parent_style=copy.copy(style or []))
                else:
                    parsed_data.append(
                        self._parse_leaf_node(
                            val, node_key, style=copy.copy(parent_style or [])
                        )
                    )
        elif (isinstance(yaml_data, list)):
            # If list add each dict element as a entry
            # using the position (index) of it as parent key using
            # brackets around it. I.e.: 'foo.[0].bar'.
            for i, e in enumerate(yaml_data):
                node_key = self._get_key_for_node('[%s]' % (i), parent_key)
                if isinstance(e, (dict, list)):
                    parsed_data = self.parse_yaml_data(
                        e, node_key, parsed_data, context,
                        parent_style=copy.copy(parent_style or []))
                else:
                    parsed_data.append(
                        self._parse_leaf_node(
                            e, node_key, style=copy.copy(parent_style or [])
                        )
                    )
        else:
            parsed_data.append(
                self._parse_leaf_node(
                    yaml_data, parent_key, style=copy.copy(parent_style or [])
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

    def get_yaml_data_to_parse(self, yaml_data):
        """ Returns the part of the yaml_data that actually need to be parsed

        In some cases only a part of the YAML structure needs to be
        processed for strings to be extracted. e.g. when the root key is the
        language code we need to exclude this from the rest of the processing.
        In the generic case the whole structure will be processed.
        """
        return yaml_data

    def parse(self, content, **kwargs):
        """ Parses the given YAML content to create stringset and template

        Steps are:
            1. Load yaml content using our custom loader TxYamlLoader that
               in addition to the value for each key notes the `start` and
               `end` index of each node in the file and some metadata.
            2. Flattens the output of the loader to be a list of the form:
               ```
               [{
                   'key': 'string_key1',
                   'value': 'string1',
                   'end': <end_index_of_node>,
                   'start': <start_index_value>,
                   'style': '|, >, ...'
                },
                ...
               ]
               ```
            3. Iterates over the flattened list and for each entry creates an
               OpenString object, appends it to stringset and replace its value
               with the template_replacement in the template.
            4. Returns the (template, stringset) tuple.
        """
        template = ""
        context = ""
        stringset = []
        yaml_data = self._load_yaml(content, loader=TxYamlLoader)
        yaml_data = self.get_yaml_data_to_parse(yaml_data)
        parsed_data = self.parse_yaml_data(yaml_data, '', [],
                                           context)
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
            comment = self._find_comment(content, end, start)
            end = end_

        template += content[end:]
        return template, stringset

    def compile(self, template, stringset, **kwargs):
        """ Compiles translation file from template

        Iterates over the stringset and for each strings replaces
        template replacement in the template with the actual translation.

        Returns the compiled file content.
        """
        transcriber = Transcriber(template)
        template = transcriber.source

        for string in stringset:
            if string.pluralized:
                tr_string = self._compile_pluralized(string)
            else:
                tr_string = self._compile_single(string)
            hash_position = template.index(string.template_replacement)
            transcriber.copy_until(hash_position)
            transcriber.add(tr_string)
            transcriber.skip(len(string.template_replacement))

        transcriber.copy_until(len(template))
        compiled = transcriber.get_destination()

        return compiled

    def _compile_pluralized(self, string):
        """ Prepare a pluralized string to be added to the template
        """
        raise NotImplemented

    def parse_pluralized_value(self, value):
        """ Creates a dictionary of the form:
        ```
        {rule_number: rule_translation, ...}
        ```
        based on a YAML node """
        raise NotImplemented

    def is_pluralized(self, val):
        """ Checks if given yml node should be handled as pluralized

        This method by default returns False because no entry in a
        generic YML file should be handled as pluralized.
        Should be overriden in any subclass that should handle pluralized
        strings """
        return False


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
            if isinstance(value, (dict, list)):
                values.append(value)
            else:
                style = value_node.style
                values.append((value, start, end, style))
        return values
