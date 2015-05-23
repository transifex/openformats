"""
    This is a hypothetical format to help demonstrate:

    a. plurals
    b. parsers and compilers that utilize a serializer

    A sample source file for this hypothetical format would be:

    {
        "greeting": "hello world",
        "unread_messages": {
            "1": "%s unread message",
            "5": "%s unread messages"
        }
    }
"""

from __future__ import absolute_import

import json

from ..handler import Handler, OpenString


class JsonHandler(Handler):
    name = "JSON"

    def parse(self, content):
        stringset = []
        parsed = json.loads(content)
        for key, value in parsed.items():
            # in JSON, keys are always strings, must convert plural rules to
            # integers
            if isinstance(value, dict):
                for rule, string in value.items():
                    value[int(rule)] = string
                    del value[rule]

            string = OpenString(key, value)
            stringset.append(string)

            parsed[key] = string.template_replacement

        template = json.dumps(parsed)
        return template, stringset

    def compile(self, template, stringset):
        template_dict = json.loads(template)
        stringset_dict = {string.key: string.string for string in stringset}
        for key in template_dict:
            template_dict[key] = stringset_dict[key]
        return json.dumps(template_dict, indent=2)
