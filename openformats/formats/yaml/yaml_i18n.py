from __future__ import absolute_import
import json
import re

from openformats.exceptions import ParseError
from openformats.formats.yaml import YamlHandler
from openformats.formats.yaml.utils import yaml


class I18nYamlHandler(YamlHandler):
    """ Internationalization specific YAML handler

    Parses and compiles YAML content the same way YamlHandler does with
    additional care for nodes representing a pluralized string and the
    root key being the language code.
    """

    name = "Yaml (Internationalization)"
    extension = "yml"
    EXTRACTS_RAW = False

    _lang_rules = []
    extra_indent = 1

    COLON_REPLACEMENT = '<COLON>'

    def set_lang_code(self, language_code):
        self.language_code = language_code

    def set_plural_rules(self, lang_rules):
        self._lang_rules = lang_rules

    def get_plural_rules(self):
        return self._lang_rules

    def is_pluralized(self, node):
        rule_names = [self.get_rule_string(r) for r in self._lang_rules]
        if not isinstance(node, dict):
            return False

        node_keys = node.keys()
        # if one of the plural rules is missing from the node keys then this is
        # not a pluralized node
        for rule in rule_names:
            if rule not in node_keys:
                return False

        # if there are extra keys make sure that they are plural rules
        extra_keys = set(node_keys) - set(rule_names)
        for key in extra_keys:
            if key not in self._RULES_ATOI.keys():
                return False

        # if any one of the values of the node contains sub nodes then this is
        # not a pluralized node. E.g.
        # test:
        #   one:
        #     nested_key: value
        #   other: other_value
        if any([isinstance(n.value, (dict, list)) for n in node.values()]):
            return False

        return True

    def _get_yaml_data_to_parse(self, yaml_data):
        keys = yaml_data.keys()
        if len(keys) > 1:
            raise ParseError("YAML file contains more than one root keys.")

        root_key = keys[0]
        return yaml_data[root_key][0]

    def _get_plural_styles(self, string):
        """
        Extract a dictionary containing the style of each plural rule.

        The flag field of the SourceEntity contain the YAML style of the plural
        rule serialized. Ancestor's styles are divided with colons. The
        plural's style dictionary is serialized and has its colons escaped.

        :param str string: The string that contains the serialized styles of
            the SourceEntity
        :return: A dictionary with containing the plural rules names as keys
            and their styles as values. If the styles can't be retrieved, an
            empty dictionary is returned

        Example:
            `block::literal:{'one'<COLON>'\'', 'other'<COLON>'"'}`
            will return:
            {'one': '\'', 'other': '"'}
        """
        plural_styles = getattr(string, 'flags', '').split(':')
        if len(plural_styles):
            try:
                return json.loads(
                    plural_styles[-1].replace(self.COLON_REPLACEMENT, ':')
                )
            except ValueError:
                # If we can't parse the plural styles for some reason, we just
                # return an empty dictionary
                pass
        return {}

    def _compile_pluralized(self, string):
        # Retrieve the styles of the plural rules that are stored in the
        # string's flag
        plural_styles_json = self._get_plural_styles(string)

        plurals = []
        for rule, translation in string.string.items():
            # If a translation contains a rule that does not exist in the
            # source language, then we inherit the style from the singular
            # version
            default_rule = self.get_rule_number('other')
            default_style = plural_styles_json.get(str(default_rule), '')
            plural_style = plural_styles_json.get(str(rule), default_style)
            # Dump a Python dictionary that contains a single plural rule as a
            # single YAML rule and preserve the string's style
            plural = yaml.safe_dump(
                {self.get_rule_string(rule): translation},
                default_flow_style=False,
                default_style=plural_style,
                allow_unicode=True,
                width=float('inf'),
            ).decode('utf-8')
            # The safe_dump method places quotes around the keys too, which are
            # unnecessary. Remove them using the regular expression below.
            plural = re.sub('^{style}(\w+){style}:'.format(style=plural_style),
                            '\g<1>:', plural)
            plurals.append(plural)

        indentation_levels = len(string.key.split('.')) + self.extra_indent
        indent = " " * indentation_levels * self.indent

        plural_entry = u''.join([
            u"{indent}{line}".format(indent=indent, line=line)
            for line in plurals
        ])

        # hash replacement in template is already indented in the template
        # so for the first line we need to keep on one level of indentation
        return plural_entry[(len(indent)-self.indent):]

    def _parse_pluralized_leaf_node(self, node, parent_key, style=[],
                                    pluralized=False):
        """Parse a leaf node in yaml_dict.
        Args:
            yaml_data: A tuple of the form (plurals_dict, start, end, style)
                      that describes a pluralized node
                      `plurals_dict` example:
                          {
                              "one": (string, start, end, style),
                              "other": (string, start, end, style)
                          }
            parent_key: A string of keys concatenated by '.' to
                        reach this node
            style: A list of YAML node styles from root node to
                   immediate parent node of the current YAML node.

        Returns:
            A dictionary representing the parsed leaf node
        """
        value, styles = self._parse_pluralized_value(node.value)
        end = self._find_pluralized_end_pos(node.value)
        style.append(node.style or '')
        # Append the plural styles dictionary to the string's style using a
        # replacement for the colon character because it is used to separate
        # the styles
        style.append(json.dumps(styles).replace(":", self.COLON_REPLACEMENT))
        return {
            'start': node.start,
            'end': end,
            'key': parent_key,
            'value': value,
            'style': ':'.join(style or []),
            'pluralized': pluralized,
        }

    def _find_pluralized_end_pos(self, node):
        """ Calculate end position of pluralized string """

        # End position for pluralized string should be the end position of
        # the last plural element and not the end position of the parent node.
        return max([entry.end for entry in node.values()])

    def _parse_pluralized_value(self, node):
        """ Parses input value into an OpenString pluralized value

        Args:
            node: a dictionary of the form
              {
                  "one": Node('string1', start, end, style),
                  "other": Node('string2', start, end, style)
              }
        Returns:
            a dictionary of the form:
              {
                  1: 'string1',
                  5: 'string2',
              }
        """
        rule_names = [self.get_rule_string(r) for r in self._lang_rules]
        value = {
            self.get_rule_number(key): entry.value
            for key, entry in node.iteritems()
            if key in rule_names
        }
        styles = {
            self.get_rule_number(key): entry.style or ''
            for key, entry in node.iteritems()
            if key in rule_names
        }
        return value, styles
