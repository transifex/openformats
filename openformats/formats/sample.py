"""
Sample OpenFormats Handler
"""

from ..handler import Handler  # , String


class SampleHandler(Handler):
    name = "SAMPLE"

    def parse(self, content):
        # stringset = []
        # parsed = parsing_library.load(content)
        # for key, value in parsed.items():
        #    string = String(key, value)
        #    stringset.append(string)
        #    parsed[key] = string.template_replacement
        # template = parsing_library.export(parsed)
        # return template, stringset
        pass

    def compile(self, template, stringset):
        # template_dict = parsing_library.loads(template)
        # stringset_dict = {string.key: string.string for string in stringset}
        # for key in template_dict:
        #     template_dict[key] = stringset_dict[key]
        # return parsing_library.export(template_dict)
        pass