from __future__ import absolute_import
import re

from mistune import (BlockLexer, Markdown)

from ..handlers import Handler
from ..strings import OpenString
from ..utils.compilers import OrderedCompilerMixin


def string_handler(string):
    'Extra checks and manipulation of extracted string from markdown file.'

    # Drop new lines around string.
    string = string.strip('\n')

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

    return string


class TxBlockLexer(BlockLexer):

    md_stringset = []

    # Overwrite to not drop `>` character from code block
    def parse_block_quote(self, m):
        self.tokens.append({'type': 'block_quote_start'})
        self.tokens.append({'type': 'block_quote_end'})

    def parse(self, text, rules=None):
        text = text.rstrip('\n')

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
                parser_rules = ('list_block', 'def_footnotes')
                if key and key not in parser_rules:
                    # Grab md string match and put in a md_stringset list.
                    self.md_stringset.append(m.group(0))

                text = text[len(m.group(0)):]
                continue
            if text:  # pragma: no cover
                raise RuntimeError('Infinite loop at: %s' % text)

        return self.tokens


class GithubMarkdownHandler(OrderedCompilerMixin, Handler):
    name = "Github Markdown"
    extension = "md"

    # Translatable YAML header attributes
    YAML_ATTR = (u'title', u'description')

    def yaml_parser(self, yaml_header):
        yaml_strings = []
        for line in yaml_header.splitlines():
            key_value = line.split(':', 1)
            if len(key_value) == 2 and key_value[0].lower() in self.YAML_ATTR:
                yaml_strings.append(key_value[1].strip())
        return yaml_strings

    def parse(self, content, **kwargs):

        template = content
        stringset = []

        yml_header = re.match(r'^(-+)\s*([\s\S]*?[^`])\s*\1(?!-)', content)
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
        for string in (yaml_stringset + block.md_stringset):
            string = string_handler(string)
            if string:
                string_object = OpenString(str(order), string, order=order)
                order += 1
                stringset.append(string_object)
                template = template.replace(
                    string, string_object.template_replacement, 1
                )
        return template, stringset
