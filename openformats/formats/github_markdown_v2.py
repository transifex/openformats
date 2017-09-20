from __future__ import absolute_import
import re

from mistune import Markdown

from openformats.formats.github_markdown import TxBlockLexer, string_handler
from openformats.formats.yaml import YamlHandler
from ..handlers import Handler
from ..strings import OpenString
from ..utils.compilers import OrderedCompilerMixin
from ..utils.newlines import find_newline_type, force_newline_type
from ..transcribers import Transcriber


class GithubMarkdownHandlerV2(OrderedCompilerMixin, Handler):
    name = "Github_Markdown_v2"
    extension = "md"
    EXTRACTS_RAW = False

    BACKSLASH = u'\\'
    DOUBLE_QUOTES = u'"'
    NEWLINE = u'\n'
    COLON = u':'
    ASTERISK = u'*'
    AMPERSAND = u'&'
    DASH = u'-'

    def _should_wrap_in_quotes(self, tr_string):
        return any([
            self.NEWLINE in tr_string[:-1],
            self.COLON in tr_string,
            tr_string.lstrip().startswith(self.ASTERISK),
            tr_string.lstrip().startswith(self.AMPERSAND),
            tr_string.lstrip().startswith(self.DASH),
        ])

    def compile(self, template, stringset, **kwargs):
        # assume stringset is ordered within the template
        transcriber = Transcriber(template)
        template = transcriber.source

        for string in stringset:
            tr_string = string.string
            try:
                # if string's key is int this is a markdown string
                int(string.key)
            except ValueError:
                if self._should_wrap_in_quotes(tr_string):
                    # escape double quotes inside strings
                    tr_string = string.string.replace(
                        self.DOUBLE_QUOTES,
                        (self.BACKSLASH + self.DOUBLE_QUOTES)
                    )
                    # surround string with double quotes
                    tr_string = (self.DOUBLE_QUOTES + tr_string +
                                 self.DOUBLE_QUOTES)
                # this is to ensure that if the style is literal or folded
                # http://www.yaml.org/spec/1.2/spec.html#id2795688
                # a new line always follows the string
                if (string.flags and string.flags in '|>' and
                        tr_string[-1] != self.NEWLINE):
                    tr_string = tr_string + self.NEWLINE

            hash_position = template.index(string.template_replacement)
            transcriber.copy_until(hash_position)
            transcriber.add(tr_string)
            transcriber.skip(len(string.template_replacement))

        transcriber.copy_until(len(template))
        compiled = transcriber.get_destination()

        return compiled

    def parse(self, content, **kwargs):
        newline_type = find_newline_type(content)
        if newline_type == 'DOS':
            content = force_newline_type(content, 'UNIX')

        # mistune expands tabs to 4 spaces and trims trailing spaces, so we
        # need to do the same in order to be able to match the substrings
        template = content.expandtabs(4)
        pattern = re.compile(r'^ +$', re.M)
        template = pattern.sub('', template)

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
                md_template = (
                    md_template[:curr_pos] + md_template[curr_pos:].replace(
                        string, string_object.template_replacement, 1)
                )

                curr_pos = md_template.find(string_object.template_replacement)
                curr_pos = curr_pos + len(string_object.template_replacement)

        template = yaml_template + seperator + md_template
        return force_newline_type(template, newline_type), stringset
