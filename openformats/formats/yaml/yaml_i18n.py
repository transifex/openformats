from __future__ import absolute_import

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

    def set_lang_code(self, language_code):
        self.language_code = language_code

    def set_plural_rules(self, lang_rules):
        self._lang_rules = lang_rules

    def get_plural_rules(self):
        return self._lang_rules

    def is_pluralized(self, val):
        rule_names = [self.get_rule_string(r) for r in self._lang_rules]
        if not isinstance(val, dict):
            return False

        return sorted(val.keys()) == sorted(rule_names)

    def _get_yaml_data_to_parse(self, yaml_data):
        keys = yaml_data.keys()
        if len(keys) > 1:
            raise ParseError("YAML file contains more than one root keys.")

        root_key = keys[0]
        return yaml_data[root_key][0]

    def _compile_pluralized(self, string):
        plurals_dict = {
            self.get_rule_string(rule): translation
            for rule, translation in string.string.items()
        }
        indentation_levels = len(string.key.split('.')) + self.extra_indent
        indent = " " * indentation_levels * self.indent

        yml_str = yaml.dump(plurals_dict, default_flow_style=False,
                            allow_unicode=True).decode('utf-8')
        plural_entry = u''.join([
            u"{indent}{line}".format(indent=indent, line=line)
            for line in yml_str.splitlines(True)
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
        value = self._parse_pluralized_value(node.value)
        end = self._find_pluralized_end_pos(node.value)
        style.append(node.style or '')
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
            value: a dictionary of the form
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
        return {
            self.get_rule_number(key):  entry.value
            for key, entry in node.iteritems()
        }
