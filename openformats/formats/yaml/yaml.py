from __future__ import absolute_import
from builtins import str

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


REMOVE_LINE_INDICATOR = '<<__TX_REMOVE_LINE__>>'


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

    # If True, all entries that have no translation will be removed
    # from the compiled string, while leaving the rest of the
    # template intact
    should_remove_empty = False

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
        self._parse_yaml_data(yaml_data, '', [], '')
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
            parents = node.get('parents')

            if not value:
                continue
            if isinstance(value, dict) and not all(six.itervalues(value)):
                continue

            string_object = OpenString(
                key, value, context=tag or '', flags=style, order=order, parents=parents
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

    def find_backwards_in_list(self, l, start_idx, compare_func):
        i = start_idx - 1
        while i >= 0:
            elem = l[i]
            if compare_func(elem):
                return i
            i -= 1
        return None

    def get_ptr_for_start_section(self, full_key, transcriber, start_idx):
        partial_key = self.get_last_partial_key(full_key)
        if re.search('\[\d+\]', partial_key):  # part of a list
            find_elem = ' - '
        else:
            find_elem = '{}:'.format(partial_key)
        # search for last previous ' - ' in string
        idx_key = self.find_backwards_in_list(transcriber.destination, start_idx, lambda x: x == find_elem)
        # look further back to include also related comments
        idx = idx_key
        while True:
            idx_comment = self.find_backwards_in_list(transcriber.destination, idx, lambda x: x.startswith("#"))
            if idx_comment == None:
                break
            else:
                idx = idx_comment
        return idx

    def add_section(self, transcriber, ptr_start, ptr_end):
        # SOS transcriber length and pointer are changed after this!!!
        transcriber.destination.insert(ptr_end + 1, transcriber.SectionEnd)
        transcriber.destination.insert(ptr_start, transcriber.SectionStart)

    def key_is_nested(self, key):
        return len(key.split('.')) > 1

    def translation_is_empty(self, string):
        return not string or (isinstance(string, dict)
                                     and not all(six.itervalues(string)))

    def get_key_data(self, transcriber, key, hash):
        """Return a tuple of:
           * transcriber ptr to the position of it's key for a given hash
           * the string in the template consisting of the key and hash combined
        """
        partial_key = self.get_last_partial_key(key)
        if re.search('\[\d+\]', partial_key):  # part of a list
            find_elem = ' - {}'.format(hash)
            return transcriber.source.find(find_elem, transcriber.ptr), find_elem
        else:
            find_elem = '- {}: {}'.format(partial_key, hash)
            ptr = transcriber.source.index(find_elem, transcriber.ptr)
            if ptr == -1:
                find_elem = '{}: {}'.format(partial_key, hash)
                ptr = transcriber.source.index(find_elem, transcriber.ptr)
            return ptr, find_elem

    def stringset_keys(self, stringset):
        """Return the keys of a stringset as keys of a dict for efficient lookups"""
        keys = {}
        i = 0
        for string in stringset:
            keys[string.key] = i
            i += 1
        return keys

    def check_children_empty(self, stringset, key):
        """Check if all children of a key in a stringset are empty"""
        for string in stringset:
            string_key = string.key
            if string_key.startswith(key):
                if not self.translation_is_empty(string.string):
                    return False
        return True

    def get_children(self, stringset, key):
        """Find last child of an ancestor node, returns an Openstring"""
        children = []
        for string in stringset:
            string_key = string.key
            if string_key.startswith(key):
                children.append(string)
        return children

    def get_last_partial_key(self, full_key):
        return full_key.split('.')[-1]

    def key_is_list(self, key):
        return re.search('\[\d+\]', key)

    def locate_in_template(self, transcriber, text, start_idx=0):
        return (transcriber.source.find(text, start_idx) > -1)

    def pos_of_key(self, key, known_key, known_key_template_text,
                   transcriber, template):
        end_pos = template.find(known_key_template_text)

    def get_ancestor_in_template(self, key, key_template_text, template):
        """key, key_template_text should be the first children node"""
        parts = key.split('.')
        if len(parts) <= 1:
            return key, key_template_text
        else:
            known_key_pos = template.find(key_template_text)
            parts.pop()
            ancestor_key = parts[-1]
            if re.search('\[\d+\]', ancestor_key):  # part of a list
                find_elem = ' - '
                pos1 = template.rfind(find_elem, known_key_pos)
                find_elem = '['
                pos2 = template.rfind(find_elem, known_key_pos)
                pos = max([pos1, pos2])
            else:
                if len(parts) > 1 and re.search('\[\d+\]', parts[-2]):
                    find_elem = ' - {}:'.format(ancestor_key)
                else:
                    find_elem = '{}:'.format(ancestor_key)
                pos = template.rfind(find_elem, known_key_pos)
            if pos > 0:
                return pos
            else:
                raise Exception('ancestor_key `{}` not found with expression:`{}`'.format(ancestor_key, find_elem))

    def get_current_key(self, full_key, transcriber, hash, start_idx=0):
        yg = YamlGenerator(self)
        parts = full_key.split('.')
        last = yg._parse_int_key(self.unescape_dots(parts.pop()))
        # import pdb; pdb.set_trace()
        ancestor = '.'.join(parts)
        if not self.key_is_list(str(last)):
            # how the key appears in the template
            in_template = '{}: {}'.format(last, hash)
            if len(parts) and self.key_is_list(parts[-1]):
                pre = parts.pop()
                last = '.'.join([pre, last])
                in_template = ' - {}'.format(in_template)
            ancestor = '.'.join(parts)
        else:
            if self.locate_in_template(transcriber, ' - {}'.format(hash), start_idx):
                in_template = ' - {}'.format(hash)
            # probably in in-line list, check variations`
            elif self.locate_in_template(transcriber, '[{}'.format(hash), start_idx):
                in_template = '[{}'.format(hash)
            elif self.locate_in_template(transcriber, '{}]'.format(hash), start_idx):
                in_template = '[{}'.format(hash)
            elif self.locate_in_template(transcriber, '{},'.format(hash), start_idx):
                in_template = '{},'.format(hash)
            elif self.locate_in_template(transcriber, '[{}]'.format(hash), start_idx):
                in_template = '[{}]'.format(hash)
            else:
                raise Exception('Cannot locate hash {} in template'.format(hash))

        # current key, ancestor key, prefix to current key, last_in_template
        if not self.locate_in_template(transcriber, in_template, start_idx):
            raise Exception('Cannot locate hash {} in template'.format(hash))
        return last, ancestor, in_template

    def first_ancestor_with_empty_children(self, key, first_key_in_template, first_key,
                                           stringset, transcriber):
        parts = key.split('.')
        if len(parts) <= 1:
            return key, first_key_in_template, first_key
        else:
            last = parts.pop()
            ancestor = '.'.join(parts)
            if not self.check_children_empty(ancestor):
                return key, first_key_in_template, first_key
            else:
                first = self.get_children(stringset, ancestor)[0]
                k, ancestor_k, k_in_template = self.get_current_key(
                    first.key, transcriber, first.template_replacement)
                return self.first_ancestor_with_empty_children(ancestor_k, k_in_template, k,
                                                               stringset, transcriber)

    def mark_section_by_text(self, transcriber, text, template):
        ptr_start = template.index(text)
        transcriber.copy_until(ptr_start)
        transcriber.mark_section_start()
        transcriber.skip(len(text))
        transcriber.mark_section_end()

    def mark_section_by_ptr(self, transcriber, ptr_start, ptr_end, template):
        transcriber.copy_until(ptr_start)
        transcriber.mark_section_start()
        transcriber.skip(ptr_end - ptr_start)
        transcriber.mark_section_end()

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
        stringset_2 = stringset
        self.indent = self._get_indent(template)
        transcriber = Transcriber(template)
        template = transcriber.source
        empty_keys = []
        section_cnt = 0

        # 1st pass, remove empty translations
        translations_removed = False
        if self.should_remove_empty:
            for string in stringset:
                import pdb; pdb.set_trace()
                pass
        #         print(u'key: {}'.format(str(string.key)))
        #         # If the string is empty or all plurals of a pluralized string
        #         # are empty, there is no translation
        #         if self.translation_is_empty(string.string) and not string.key in empty_keys:
        #             # import pdb; pdb.set_trace()
        #
        #             translation = None
        #             translations_removed = True
        #             k, ancestor_k, k_in_template = self.get_current_key(
        #                 string.key, transcriber, string.template_replacement)
        #             if self.key_is_nested(string.key):
        #                 # lookup ancestor node's children, are all empty?
        #                 if not self.check_children_empty(ancestor_k):
        #                     # not all empty, just mark the current key for removal
        #                     self.mark_section_by_text(transcriber, k_in_template, template)
        #                     empty_keys.append(string.key)
        #                     section_cnt += 1
        #                 else:
        #                     # all child nodes empty
        #                     # lookup previous ancestor (same logic) until you find starting node
        #                     # find last empty child node (to mark section end)
        #                     first_ancestor_k, first_in_template, first_key = \
        #                         self.first_ancestor_with_empty_children(ancestor_k,
        #                                                                 k_in_template, k,
        #                                                                 stringset)
        #                     ancestor = ancestor_k if first_ancestor_k == ancestor_k else first_ancestor_k
        #                     start_pos = self.get_ancestor_in_template(ancestor, first_in_template, template)
        #                     children = self.get_children(stringset, ancestor)
        #                     last = children[-1]
        #                     last_pos = template.index(last.template_replacement) + len(last.template_replacement)
        #                     self.mark_section_by_ptr(transcriber, start_pos, last_pos, template)
        #                     empty_keys.extend(list(map(lambda child: child.key, children)))
        #                     section_cnt += 1
        #             else:
        #                 # mark start - end section in place
        #                 self.mark_section_by_text(transcriber, k_in_template, template)
        #                 empty_keys.append(string.key)
        #                 section_cnt += 1
        #
        #     transcriber.copy_until(len(template))
        #     for i in range(1, section_cnt+1):
        #         transcriber.remove_section()
        #     template = transcriber.get_destination()
        #     stringset_2 = [string
        #                    for string in stringset
        #                    if string.key not in empty_keys]


        transcriber = Transcriber(template)
        # template = transcriber.source
        for string in stringset_2:
            print(u'key: {}'.format(str(string.key)))
            # If the string is empty or all plurals of a pluralized string
            # are empty, there is no translation
            if not string.string or (isinstance(string.string, dict)
                                     and not all(six.itervalues(string.string)
                                                 )):
                translation = None
            elif string.pluralized:
                translation = self._compile_pluralized(string)
            else:
                translation = self._write_styled_literal(string)

            hash_position = template.index(string.template_replacement)
            transcriber.copy_until(hash_position)

            # The context contains custom tags. If it exists, we must prepend
            # it and apply a space afterwards so it doesn't get merged with the
            # string
            if string.context:
                transcriber.add(string.context)
                transcriber.add(' ')
            transcriber.add(translation)

            # If there is no translation for this string, mark the entry
            # so that it can later be removed
            if self.should_remove_empty and not translation:
                transcriber.add(REMOVE_LINE_INDICATOR)
                translations_removed = True
                # ptr_end = transcriber.ptr
                # ptr_start = self.get_ptr_for_start_section(string.key, transcriber, ptr_end)
                # self.add_section(transcriber, ptr_start, ptr_end)
                # add section changes transcriber length so must fix ptr
                # transcriber.ptr = len(transcriber.destination) - 1
                # # store ptr of empty translation
                # empty_ptrs.append(transcriber.ptr - 1) # last is end section

                # If folded style is used, we need to add an extra newline,
                # otherwise the next entry will be on the same line as
                # the indicator, and will also be removed
                style = string.flags.split(':')[-1]
                if style == '>' or style == '|':
                    transcriber.add('\n')

            transcriber.skip(len(string.template_replacement))

        transcriber.copy_until(len(template))
        compiled = transcriber.get_destination()

        # # add nested sections for nested keys
        # for string in stringset:
        #     if not string.string or (isinstance(string.string, dict)
        #                              and not all(six.itervalues(string.string)
        #                                          )):
        #         pass
        # remove sections

        # Remove lines that are marked for removal, if they exist
        # For any removed string, any comment lines that proceed it
        # should also be removed
        # if translations_removed:
        #     string = StringIO(compiled)
        #     output = StringIO()
        #     current_output = StringIO()
        #     current_comment = StringIO()
        #
        #     while True:
        #         line = string.readline()
        #         # End of string
        #         if not line:
        #             break
        #
        #         # Marked for removal; get rid of the corresponding comments
        #         # and skip the line altogether
        #         if REMOVE_LINE_INDICATOR in line:
        #             current_comment = StringIO()
        #             current_output = StringIO()
        #             continue
        #
        #         # A comment line was found; keep to check later
        #         # if it should be added or not
        #         if line.lstrip().startswith('#'):
        #             current_comment.write(line)
        #             continue
        #         else:
        #             current_output.write(line)
        #
        #         # Write any comments and reset
        #         output.write(current_comment.getvalue())
        #         current_comment = StringIO()
        #
        #         # Write the actual line
        #         output.write(current_output.getvalue())
        #         current_output = StringIO()
        #
        #     # There might be comments left in the end, so write them now
        #     output.write(current_comment.getvalue())
        #     compiled = output.getvalue()

        return compiled

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

    def _parse_leaf_node(self, node, parent_key, parents, style=[],
                         pluralized=False):
        """Parse a leaf node in yaml_dict.
        Args:
            node: A tuple of the form (string, start, end, style, tag)
            parent_key: A string of keys concatenated by '.' to
                reach this node
            parents: the list of the chain of parent nodes leading to
                the current leaf node - string. Each list item consists
                of a tuple in the form of:

                (<parent_key>, <start_pos>, <end_pos>)

                where <parent_key> is the combined parent key of each parent
                node (see parent_key above), <start/end_pos> is the integer
                position in content where the value of the parent node
                starts/ends.
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
            'parents': parents,
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

    def _parse_yaml_data(self, yaml_data, parent_key, parents, context="",
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
            parents: the list of the chain of parent nodes leading to
                the current leaf node - string. Each list item consists
                of a tuple in the form of:

                (<parent_key>, <start_pos>, <end_pos>)

                where <parent_key> is the combined parent key of each parent
                node (see parent_key above), <start/end_pos> is the integer
                position in content where the value of the parent node
                starts/ends.
            context: A string
            parent_style: A list of YAML node styles for each parent node.

        Returns:
            A list of dictionaries, where each dictionary maps a node
            key to its value
        """
        parent_style = parent_style or []

        parents_copy = [] if parent_key == '' else copy.deepcopy(parents)
        if isinstance(yaml_data, dict):
            for key, node in six.iteritems(yaml_data):
                parents_copy = [] if parent_key == '' else parents_copy
                node_key = self._get_key_for_node(key, parent_key)
                # Copy style for each node to avoid getting affected from the
                # previous loops
                node_style = copy.copy(parent_style)
                # Case of dictionary that represents a plural rule
                if (isinstance(node.value, dict) and
                        self.is_pluralized(node.value)):
                    self._parsed_data.append(
                        self._parse_pluralized_leaf_node(
                            node, node_key, parents_copy,
                            style=node_style,
                            pluralized=True
                        )
                    )
                    parents_copy = []
                # Handle dictionaries and lists
                elif isinstance(node.value, (dict, list)):
                    node_style.append(node.style or '')
                    parents_copy.append((node_key, node.start, node.end))
                    self._parse_yaml_data(node.value, node_key, parents_copy, context,
                                          parent_style=node_style)
                    parents_copy.pop()
                # Otherwise handle the node as a leaf
                else:
                    self._parsed_data.append(
                        self._parse_leaf_node(
                            node, node_key, parents_copy, style=node_style
                        )
                    )
        elif (isinstance(yaml_data, list)):
            # If list add each dict element as an entry
            # using the position (index) of it as parent key using
            # brackets around it. I.e.: 'foo.[0].bar'.
            for i, node in enumerate(yaml_data):
                parents_copy = [] if parent_key == '' else parents_copy
                node_key = self._get_key_for_node('[{}]'.format(i), parent_key)
                # Copy style for each node to avoid getting affected from the
                # previous loops
                node_style = copy.copy(parent_style)
                if isinstance(node.value, (dict, list)):
                    node_style.append(node.style or '')
                    parents_copy.append((node_key, node.start, node.end))
                    self._parse_yaml_data(node.value, node_key, parents_copy, context,
                                          parent_style=node_style)
                    parents_copy.pop()
                else:
                    self._parsed_data.append(
                        self._parse_leaf_node(
                            node, node_key, parents_copy, style=node_style
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
        emitter.stream.close()
        return translation

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
