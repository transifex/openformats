from __future__ import absolute_import, unicode_literals

import re

import six
import unicodedata
from mistune import BlockGrammar, Markdown, _block_tag, _pure_pattern

from openformats.formats.github_markdown import TxBlockLexer, string_handler
from openformats.formats.github_markdown_v2 import GithubMarkdownHandlerV2
from openformats.formats.yaml import YamlHandler
from openformats.utils.compat import ensure_unicode

from ..strings import OpenString
from ..utils.newlines import find_newline_type, force_newline_type


class TxBlockGrammarV2_1(BlockGrammar):
    # CommonMark allows an arbitrary info string after the language id on a
    # fenced code block (e.g. ```js lines, ```python {linenos=true}). mistune
    # 0.8 only accepts a single \S+ token followed by spaces, so anything
    # extra makes the fence rule fail and the block falls into `paragraph`,
    # which then also swallows any following heading because the closing ```
    # is no longer recognised on its own.
    fences = re.compile(
        ensure_unicode(
            r'^ *(`{3,}|~{3,}) *(\S+)?[^\n]*\n'
            r'([\s\S]+?)\s*'
            r'\1 *(?:\n+|$)'
        )
    )
    # `paragraph` embeds `fences` in a lookahead, so it has to be rebuilt
    # against the permissive pattern above; otherwise paragraph still uses
    # the strict mistune default and keeps consuming through fenced blocks
    # whose info strings carry extra metadata.
    paragraph = re.compile(
        ensure_unicode(
            r'^((?:[^\n]+\n?(?!'
            r'%s|%s|%s|%s|%s|%s|%s|%s|%s'
            r'))+)\n*'
        ) % (
            _pure_pattern(fences).replace(r'\1', r'\2'),
            _pure_pattern(BlockGrammar.list_block).replace(r'\1', r'\3'),
            _pure_pattern(BlockGrammar.hrule),
            _pure_pattern(BlockGrammar.heading),
            _pure_pattern(BlockGrammar.lheading),
            _pure_pattern(BlockGrammar.block_quote),
            _pure_pattern(BlockGrammar.def_links),
            _pure_pattern(BlockGrammar.def_footnotes),
            '<' + _block_tag,
        )
    )


class TxBlockLexerV2_1(TxBlockLexer):
    grammar_class = TxBlockGrammarV2_1


class GithubMarkdownHandlerV2_1(GithubMarkdownHandlerV2):
    name = "Github_Markdown_v2_1"

    # Use the V2_1 lexer so the permissive fences/paragraph grammar kicks in.
    def _get_block_lexer(self):
        return TxBlockLexerV2_1()
