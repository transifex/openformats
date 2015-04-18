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

from ..handler import Handler, String
from ..utils.test import test_handler


class JsonHandler(Handler):
    name = "JSON"

    def feed_content(self, content):
        parsed = json.loads(content)
        for key, value in parsed.items():
            # in JSON, keys are always strings, must convert plural rules to
            # integers
            if isinstance(value, dict):
                for rule, string in value.items():
                    value[int(rule)] = string
                    del value[rule]

            string = String(key, value)
            yield string

            parsed[key] = string.template_replacement

        self.template = json.dumps(parsed)

    def compile(self, stringset):
        template_dict = json.loads(self.template)
        stringset_dict = {string.key: string.string for string in stringset}
        for key in template_dict:
            template_dict[key] = stringset_dict[key]
        return json.dumps(template_dict, indent=2)


def main():
    test_handler(JsonHandler, '''
        {
            "foo1": "Hello world",
            "foo2": "Kostas",
            "foo3": "Ioanna",
            "foo4": "Ariadne",
            "foo5": "Victor",
            "foo6": {
                "1": "%s message",
                "5": "%s messages"
            }
        }
    ''')


if __name__ == "__main__":
    main()
