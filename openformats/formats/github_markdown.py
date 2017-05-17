from __future__ import absolute_import
import re

from mistune import (BlockLexer, Markdown)

from ..handlers import Handler
from ..strings import OpenString
from ..utils.compilers import OrderedCompilerMixin


def string_handler(token, template):
    """
    Extra checks and manipulation of extracted string from markdown file.
    Parameters:
    token: Tuple of (string, string_type) where string_type refers to the
           type of markdown element this string belongs to. string_type
           can be None.
    template: the template of the resource

    returns: the manipulated string or None in case the manipulated string
             is not valid anymore e.g. empty string
    """

    # Drop new lines around string.
    string, key = token
    string = string.strip('\n')

    # for code blocks we need to maintain the exact indentation as in
    # the source file both for matching the string and replacing it in the
    # template and for producing a valid markdown on compilation
    if key == 'block_code':
        lines = string.split('\n')
        line = lines[0]
        spaces = re.findall(r'\n( *){}'.format(re.escape(line)), template)[0]
        if spaces:
            string = ''
            for l in lines:
                l = '{}{}'.format(spaces, l)
                string += '\n'
                string += l

    # Line is a liquid template tag, ignore.
    if string.startswith('{%') and string.endswith('%}'):
        return

    # Drop # chars from beginning of the string
    match_header_line = re.search(r'^#+\s', string)
    if match_header_line:
        return string.replace(match_header_line.group(), '')

    # Extract Text from `[Text](link)` or `"[Text](link)"` lines
    match_link = re.search(r'^"?\[(.+)\]\(.+\)"?$', string)
    if match_link:
        # Get content between brackets
        return match_link.groups()[0]

    # Extract Text from `[Text]: link` or `"[Text]: link"` lines
    match_reference = re.search(r'^"?\[(.+)\]:.+"?$', string)
    if match_reference:
        try:
            int(match_reference.groups()[0])
        except ValueError:
            # Get content between brackets if it's not an integer number
            return match_reference.groups()[0]
        return

    # exclude numeric values from stringset
    try:
        float(string)
        return
    except ValueError:
        pass

    return string


class TxBlockLexer(BlockLexer):

    md_stringset = []

    # Overwritten to not drop `>` character from quote block
    def parse_block_quote(self, m):
        self.tokens.append({'type': 'block_quote_start'})
        self.tokens.append({'type': 'block_quote_end'})

    def parse(self, text, rules=None):
        text = text.rstrip('\n')
        parser_rules = ('list_block', 'def_footnotes')
        table_rules = ('table', 'nptable')

        if not rules:
            rules = self.default_rules

        def manipulate(text):
            for key in rules:
                rule = getattr(self.rules, key)
                m = rule.match(text)
                if not m:
                    continue
                getattr(self, 'parse_%s' % key)(m)
                return key, m
            return False  # pragma: no cover
        while text:
            m = manipulate(text)
            if isinstance(m, tuple):
                key, m = m
            else:
                key = False
            if m is not False:

                # The following parser rules called by `manipulate` call
                # `self.parse` recursively. We don't catch matches for such
                # methods to avoid getting duplicated parts of the markdown
                # content in the `self.md_stringset` because of the recursion.
                if key and key in table_rules:
                    table_token = self.tokens[-1]
                    keys = table_token.keys()
                    if 'header' in keys and 'cells' in keys:
                        self.md_stringset.extend(
                            [(h, 'header') for h in table_token['header']])
                        self.md_stringset.extend(
                            [(cell, 'cell') for row in table_token['cells']
                                for cell in row]
                        )
                elif key and key not in parser_rules:
                    # Grab md string match and put in a md_stringset list.
                    self.md_stringset.append((m.group(0), key))

                text = text[len(m.group(0)):]
                continue
            if text:  # pragma: no cover
                raise RuntimeError('Infinite loop at: %s' % text)

        return self.tokens


class GithubMarkdownHandler(OrderedCompilerMixin, Handler):
    name = "Github_Markdown"
    extension = "md"

    # Translatable YAML header attributes
    YAML_ATTR = (u'title', u'description')

    def yaml_parser(self, yaml_header):
        # TODO: This is a temporary solution. Yaml header should be parsed
        # with an actual yaml parser when it is implemented in openformats
        yaml_strings = []
        block = False
        block_string = ''
        indent = 0
        for line in yaml_header.splitlines():
            # ignore comments
            if line.startswith('#'):
                continue
            if block:
                # at least 2 spaces more indented that the parent line
                if line.startswith(' ' * (indent + 2)):
                    block_string += line
                    block_string += '\n'
                    continue
                else:
                    yaml_strings.append((block_string, None))
                    block_string = ''
                    block = False
            key_value = line.split(':', 1)
            if len(key_value) == 2:
                value = key_value[1].strip()
                # we parse all the lines that follow the '|' or '>' symbols
                # and are at least 2 spaces more intented that the parent line
                # as one string
                if value and value in '|>[':
                    indent = len(re.search(r'^( *)', key_value[0]).group(0))
                    block = True
                    continue
                yaml_strings.append((value, None))
        return yaml_strings

    def parse(self, content, **kwargs):

        template = content
        stringset = []

        yml_header = re.match(r'^(---\s+)([\s\S]*?[^`])\s*(\n---\s+)(?!-)',
                              content)
        yaml_header_content = ''
        yaml_stringset = []
        if yml_header:
            yaml_header_content = yml_header.group()
            md_content = content[len(yaml_header_content):]
            yaml_stringset = self.yaml_parser(yaml_header_content)
        else:
            md_content = content

        block = TxBlockLexer()
        markdown = Markdown(block=block)

        # Making sure stringset is empty because of recursive inside `markdown`
        block.md_stringset = []

        # Command that populates block.stringset var
        markdown(md_content)

        order = 0
        curr_pos = 0
        for string in (yaml_stringset + block.md_stringset):
            string = string_handler(string, template)
            if string:
                string_object = OpenString(str(order), string, order=order)
                order += 1
                stringset.append(string_object)
                # Keep track of the index of the last replaced hash
                template = template[:curr_pos] + template[curr_pos:].replace(
                    string, string_object.template_replacement, 1
                )
                curr_pos = template.find(string_object.template_replacement)
                curr_pos = curr_pos + len(string_object.template_replacement)
        return template, stringset
