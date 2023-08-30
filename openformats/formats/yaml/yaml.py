from __future__ import absolute_import

import copy
import re

import six
from yaml.constructor import SafeConstructor
from yaml.emitter import Emitter

from openformats.exceptions import ParseError
from openformats.formats.yaml.utils import (TxYamlDumper, TxYamlLoader,
                                            YamlGenerator, yaml)
from openformats.handlers import Handler
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from openformats.utils.compat import ensure_unicode

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class YamlHandler(Handler):
    name = "Yaml"
    extension = "yml"
    EXTRACTS_RAW = False

    # number of spaces used for indentation in YAML content
    indent = 2

    # the levels of indentation of a string can be extracted by doing
    # `len(keys.split('.'))`. For files that we ignore the root key
    # (e.g ruby i18n files) we need to set an extra level of indentation
    # `extra_indent = 1`
    extra_indent = 0

    # When compiling for a mode that needs to completely remove
    # an entry from the compiled file we cannot use the template for
    # compilation but we need to construct the YAML file from scratch
    # only with the subset of included entries.
    should_use_template = True

    language_code = None

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
        template = []
        stringset = []
        # The first argument of the add_constructor method is the tag you want
        # to handle. If you provide None as an argument, all the unknown tags
        # will be handled by the constructor specified in the second argument.
        # We need this in order parse all unknown custom-tagged values as
        # strings.
        SafeConstructor.add_constructor(None,
                                        SafeConstructor.construct_yaml_str)
        yaml_data = self._load_yaml(content, loader=TxYamlLoader)
        yaml_data = self._get_yaml_data_to_parse(yaml_data)
        # Helper to store the processed data while parsing the file
        self._parsed_data = []
        self._parse_yaml_data(yaml_data, '', '')
        self._parsed_data = sorted(self._parsed_data,
                                   key=lambda node: node.get('start'))

        end = 0
        order = 0
        for node in self._parsed_data:
            start = node.get('start')
            end_ = node.get('end')
            key = node.get('key')
            tag = node.get('tag')
            value = node.get('value')
            style = node.get('style')
            if not value:
                continue
            if isinstance(value, dict) and not all(six.itervalues(value)):
                continue
            string_object = OpenString(
                key, value, context=tag or '', flags=style, order=order,
            )
            stringset.append(string_object)
            order += 1
            template.append(u"{}{}".format(content[end:start],
                                           string_object.template_replacement))
            comment = self._find_comment(content, end, start)
            string_object.developer_comment = comment
            end = end_

        template.append(content[end:])
        template = u''.join(template)
        return template, stringset

    def compile(self, template, stringset, **kwargs):
        """
        Dump YAML content for a resource translation taking
        into account the mode used for compilation.

        Args:
            template: Template content for the resource.
            stringset: The resource's stringset.

        Returns:
            A unicode, dumped YAML content.
        """
        self.indent = self._get_indent(template)
        if self.should_use_template:
            return self._compile_from_template(template, stringset)
        else:
            return self._compile_without_template(stringset)

    def _load_yaml(self, content, loader):
        """
        Loads a YAML stream and returns a dictionary
        representation for YAML data

        Args:
            content: A string, YAML content
            loader: YAML Loader class or None

        Returns:
            A dictionary
        """
        try:
            return yaml.load(content, Loader=loader)
        except yaml.scanner.ScannerError as e:
            raise ParseError(six.text_type(e))
        except Exception as e:
            raise ParseError(six.text_type(e))

    def _parse_leaf_node(self, node, parent_key, style=[],
                         pluralized=False):
        """Parse a leaf node in yaml_dict.
        Args:
            node: A tuple of the form (string, start, end, style, tag)
            parent_key: A string of keys concatenated by '.' to
                reach this node
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        style.append(node.style or '')
        return {
            'start': node.start,
            'end': node.end,
            'key': parent_key,
            'value': node.value,
            'tag': node.tag,
            'style': ':'.join(style or []),
            'pluralized': pluralized,
        }

    def _parse_pluralized_leaf_node(self, yaml_data, parent_key, style=[],
                                    pluralized=False):
        """Parse a leaf node in yaml_dict.
        Args:
            yaml_data: A tuple of the form
                      (plurals_dict, start, end, style, tag) that describes a
                      pluralized node `plurals_dict` example:
                          {
                              "one": (string, start, end, style, tag),
                              "other": (string, start, end, style, tag)
                          }
            parent_key: A string of keys concatenated by '.' to
                        reach this node
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        raise NotImplementedError

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
        if not isinstance(key, (six.binary_type, six.text_type)):
            # Int keys are stored in < and > around it, so it can be reverted
            # on int again on compiling.
            key = u'<{}>'.format(key)
        if '.' in key:
            key = self.escape_dots(key)
        if parent_key == '':
            parent_key += key
        else:
            parent_key += '.' + key
        return parent_key

    def _parse_yaml_data(self, yaml_data, parent_key, context="",
                         parent_style=None):
        """
        Parse data returned by YAML loader

        yaml_data can be either a dict like:
            {"key1": node1, "key2": node2, ...}
        or a list like:
            [node1, node2, ...]

        Node objects above are instances of the Node namedtuple with valid
        keys ['value', 'start', 'end', 'style']. node.value can be either
        another `yaml_data` object or a string.

        Args:
            yaml_data: The output of yaml.loads()
            parent_key: A string of keys concatenated by '.' to
                        reach this node,
            context: A string
            parent_style: A list of YAML node styles for each parent node.

        Returns:
            A list of dictionaries, where each dictionary maps a node
            key to its value
        """
        parent_style = parent_style or []

        if isinstance(yaml_data, dict):
            for key, node in six.iteritems(yaml_data):
                node_key = self._get_key_for_node(key, parent_key)
                # Copy style for each node to avoid getting affected from the
                # previous loops
                node_style = copy.copy(parent_style)
                # Case of dictionary that represents a plural rule
                if (isinstance(node.value, dict) and
                        self.is_pluralized(node.value)):
                    self._parsed_data.append(
                        self._parse_pluralized_leaf_node(
                            node, node_key,
                            style=node_style,
                            pluralized=True
                        )
                    )
                # Handle dictionaries and lists
                elif isinstance(node.value, (dict, list)):
                    node_style.append(node.style or '')
                    self._parse_yaml_data(node.value, node_key, context,
                                          parent_style=node_style)
                # Otherwise handle the node as a leaf
                else:
                    self._parsed_data.append(
                        self._parse_leaf_node(
                            node, node_key, style=node_style
                        )
                    )
        elif (isinstance(yaml_data, list)):
            # If list add each dict element as an entry
            # using the position (index) of it as parent key using
            # brackets around it. I.e.: 'foo.[0].bar'.
            for i, node in enumerate(yaml_data):
                node_key = self._get_key_for_node('[%s]' % (i), parent_key)
                # Copy style for each node to avoid getting affected from the
                # previous loops
                node_style = copy.copy(parent_style)
                if isinstance(node.value, (dict, list)):
                    node_style.append(node.style or '')
                    self._parse_yaml_data(node.value, node_key, context,
                                          parent_style=node_style)
                else:
                    self._parsed_data.append(
                        self._parse_leaf_node(
                            node, node_key, style=node_style
                        )
                    )

    def _find_comment(self, content, start, end):
        """ Finds comment lines that precede a part of the YAML structure """
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
            return ''

    def _get_yaml_data_to_parse(self, yaml_data):
        """ Returns the part of the yaml_data that actually need to be parsed

        In some cases only a part of the YAML structure needs to be processed
        for strings to be extracted. e.g. when the root key is the language
        code we need to exclude this from the rest of the processing.

        Subclasses can override the default behavior, by returning a subset
        of the whole structure.
        """
        return yaml_data

    def _write_styled_literal(self, string):
        """ Produce a properly formatted YAML string

        Properly format translation string based on string's style
        on the original source file using yaml.emitter.Emitter class.

        Args:
            string: An OpenString instance

        Returns:
            The formatted string.
        """
        if string.flags is None:
            return string.string

        stream = StringIO()
        emitter = Emitter(stream, allow_unicode=True)
        indent = self.indent * (len(string.key.split('.')) + self.extra_indent)
        emitter.indent = indent
        # set best_width to `float(inf)` so that long strings are not broken
        # into multiple lines
        emitter.best_width = float('inf')

        analysis = emitter.analyze_scalar(string.string)

        style = string.flags.split(':')[-1]

        if style == '"':
            emitter.write_double_quoted(string.string)
        elif style == '\'':
            if analysis.allow_single_quoted:
                emitter.write_single_quoted(string.string)
            else:
                emitter.write_double_quoted(string.string)
        elif style == '':
            if analysis.allow_block_plain and analysis.allow_flow_plain:
                emitter.write_plain(string.string)
            else:
                emitter.write_double_quoted(string.string)
        elif style == '|':
            emitter.write_literal(string.string)
        elif style == '>':
            emitter.write_folded(string.string)

        translation = emitter.stream.getvalue() or string.string
        if translation.startswith(">-") and not translation.endswith("\n"):
            translation += "\n"
        emitter.stream.close()
        return translation

    def _compile_from_template(self, template, stringset, **kwargs):
        """ Compiles translation file from template

        Iterates over the stringset and for each strings replaces
        template replacement in the template with the actual translation.

        Returns:
            The compiled file content.
        """
        transcriber = Transcriber(template)
        template = transcriber.source

        for string in stringset:
            if string.pluralized:
                translation = self._compile_pluralized(string)
            else:
                translation = self._write_styled_literal(string)
            hash_position = template.index(string.template_replacement)
            transcriber.copy_until(hash_position)
            # The context contains custom tags. If it exists, we must prepend
            # it and apply a space afterwards so it doesn't get merged with the
            # string
            if string.context:
                # add an exclamation mark to the context to make it a tag
                transcriber.add('!' + string.context)
                transcriber.add(' ')
            transcriber.add(translation)
            transcriber.skip(len(string.template_replacement))

        transcriber.copy_until(len(template))
        compiled = transcriber.get_destination()

        return compiled

    def _compile_without_template(self, stringset):
        yg = YamlGenerator(self)
        yaml_dict = yg.generate_yaml_dict(stringset)
        if self.language_code:
            yaml_dict = self._wrap_yaml_dict(yaml_dict, self.language_code)
        return_value = yaml.dump(yaml_dict, width=float('inf'),
                                 Dumper=TxYamlDumper, allow_unicode=True,
                                 indent=self.indent)
        if isinstance(return_value, six.binary_type):
            return_value = return_value.decode("utf-8")
        return return_value

    @staticmethod
    def unescape_dots(k):
        """ Replace <TX_DOT> placeholder with a dot. """
        return k.replace('<TX_DOT>', '.')

    @staticmethod
    def escape_dots(k):
        """ We use dots to construct the strings key, so we need to
        escape dots that are part of an actual YAML key """
        return k.replace('.', '<TX_DOT>')

    def _get_indent(self, template):
        """
        Use a regular expression to figure out how many spaces are used
        for indentation in the original file.

        Args:
            template: The saved template
        Returns:
            The number of spaces.
        """
        # Match all whitespace characters after first `:` (end of first  key).
        # Stops on first non whitespace character.
        indent_pattern = re.compile(
            ensure_unicode(r':\r?\n(?P<indent>[ \t\n]+)')
        )
        m = indent_pattern.search(template)
        indent = m.groups('indent')[0] if m else ' ' * 2
        # keep only last line
        indent = indent.splitlines()[-1]
        indent = indent.replace('\t', ' ' * 4)
        return len(indent)

    def _compile_pluralized(self, string):
        """ Prepare a pluralized string to be added to the template
        """
        raise NotImplementedError

    def parse_pluralized_value(self, value):
        """ Creates a dictionary of the form:
        ```
        {rule_number: rule_translation, ...}
        ```
        based on a YAML node """
        raise NotImplementedError

    def is_pluralized(self, val):
        """ Checks if given YAML node should be handled as pluralized

        This method by default returns False because no entry in a
        generic YML file should be handled as pluralized.
        Should be overriden in any subclass that should handle pluralized
        strings """
        return False

    def _wrap_yaml_dict(self, yaml_dict, lang_code=None):
        """
        Update YAML dictionary with *language code* as the
        root of the dictionary.

        Args:
            yaml_dict: A Dictionary/OrderedDict instance.
            lang_code: A language code string.

        Returns:
            A Dictionary instance.
        """
        if lang_code:
            yaml_dict = {lang_code: yaml_dict}
        return yaml_dict
