from __future__ import absolute_import

from openformats.formats.yaml import YamlHandler
from openformats.formats.yaml.utils import yaml


class I18nYamlHandler(YamlHandler):
    name = "Yaml (Internationalization)"
    extension = "yml"
    EXTRACTS_RAW = False

    _lang_rules = []
    extra_indent = 1

    def _compile_pluralized(self, string):
        plurals_dict = {
            self.get_rule_string(rule): translation
            for rule, translation in string.string.items()
        }
        indentation_levels = len(string.key.split('.')) + self.extra_indent
        indent = " " * indentation_levels * self.indent

        yml_str = yaml.dump(plurals_dict, default_flow_style=False,
                            allow_unicode=True)
        return ''.join([
            "{indent}{line}".format(indent=indent, line=line)
            for line in yml_str.splitlines(True)
        ])[(len(indent)-self.indent):]

    def set_lang_code(self, language_code):
        self.language = language_code

    def is_pluralized(self, val):
        rule_names = [self.get_rule_string(r) for r in self._lang_rules]
        if not isinstance(val, dict):
            return False

        return sorted(val.keys()) == sorted(rule_names)

    def set_plural_rules(self, lang_rules):
        self._lang_rules = lang_rules

    def get_plural_rules(self):
        return self._lang_rules

    def parse_pluralized_value(self, value):
        return {
            self.get_rule_number(key): val[0]
            for key, val in value.iteritems()
        }

    def get_yaml_data_to_parse(self, yaml_data):
        try:
            keys = yaml_data.keys()
        except AttributeError:
            return yaml_data
        else:
            return yaml_data[keys[0]][0]
