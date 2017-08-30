from __future__ import absolute_import
import re

from mistune import Markdown

from openformats.formats.github_markdown import TxBlockLexer, string_handler
from openformats.formats.yaml import YamlHandler
from ..handlers import Handler
from ..strings import OpenString
from ..utils.compilers import OrderedCompilerMixin


class GithubMarkdownHandlerV2(OrderedCompilerMixin, Handler):
    name = "Github_Markdown_v2"
    extension = "md"

    def parse(self, content, **kwargs):

        stringset = []

        yml_header = re.match(r'^(---\s+)([\s\S]*?[^`]\s*)(\n---\s+)(?!-)',
                              content)
        yaml_header_content = ''
        yaml_stringset = []
        yaml_template = ''
        seperator = ''
        if yml_header:
            yaml_header_content = ''.join(yml_header.group(1, 2))
            seperator = yml_header.group(3)
            md_content = content[len(yaml_header_content + seperator):]
            yaml_stringset, yaml_template = YamlHandler().parse(
                yaml_header_content)
        else:
            md_content = content

        md_template = md_content

        block = TxBlockLexer()
        markdown = Markdown(block=block)

        # Making sure stringset is empty because of recursive inside `markdown`
        block.md_stringset = []

        # Command that populates block.stringset var
        markdown(md_content)

        stringset.extend(yaml_stringset)
        order = len(stringset)
        curr_pos = 0
        for string in block.md_stringset:
            string = string_handler(string, md_template)
            if string:
                string_object = OpenString(str(order), string, order=order)
                order += 1
                stringset.append(string_object)
                # Keep track of the index of the last replaced hash
                md_template = md_template[:curr_pos] + md_template[curr_pos:].replace(
                    string, string_object.template_replacement, 1
                )
                curr_pos = md_template.find(string_object.template_replacement)
                curr_pos = curr_pos + len(string_object.template_replacement)

        template = yaml_template + seperator + md_template
        return template, stringset
