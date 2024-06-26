from __future__ import absolute_import, unicode_literals

import re

import six
import unicodedata
from mistune import Markdown
from yaml.reader import Reader

from openformats.formats.github_markdown import TxBlockLexer, string_handler
from openformats.formats.yaml import YamlHandler
from openformats.utils.compat import ensure_unicode

from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.compilers import OrderedCompilerMixin
from ..utils.newlines import find_newline_type, force_newline_type


class GithubMarkdownHandlerV2(OrderedCompilerMixin, Handler):
    name = "Github_Markdown_v2"
    extension = "md"
    EXTRACTS_RAW = False

    BACKSLASH = '\\'
    DOUBLE_QUOTES = '"'
    SINGLE_QUOTE = u"'"
    NEWLINE = '\n'
    COLON = ':'
    ASTERISK = '*'
    AMPERSAND = '&'
    DASH = '-'
    HASHTAG = '#'
    AT_SIGN = '@'  # reserved character in the YAML spec
    BRACKET_LEFT = '['
    BRACKET_RIGHT = ']'
    PIPE = '|'

    # A string that looks like '\u0008'
    ESCAPED_UNICODE = re.compile(r'\\u[a-fA-F0-9]{4}')
    # ... or '\x2D'
    ESCAPED_UNICODE_HEX = re.compile(r'\\x[a-fA-F0-9]{2}')

    def compile(self, template, stringset, **kwargs):
        # assume stringset is ordered within the template
        transcriber = Transcriber(template)
        template = transcriber.source

        for openstring in stringset:
            tr_string = openstring.string
            if self._is_yaml_string(openstring):
                self._escape_invalid_chars(openstring)
                tr_string = self._transform_yaml_string(openstring)

            hash_position = template.index(openstring.template_replacement)
            transcriber.copy_until(hash_position)
            transcriber.add(tr_string)
            transcriber.skip(len(openstring.template_replacement))

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
        pattern = re.compile(ensure_unicode(r'^ +$'), re.M)
        content = unicodedata.normalize('NFKC', pattern.sub('', template))

        stringset = []

        yml_header = re.match(
            ensure_unicode(r'^(---\s+)([\s\S]*?[^`]\s*)(\n---\s+)(?!-)'),
            content
        )
        yaml_header_content = ''
        yaml_stringset = []
        yaml_template = ''
        seperator = ''

        if yml_header:
            yaml_header_content = ''.join(yml_header.group(1, 2))
            seperator = yml_header.group(3)
            md_content = content[len(yaml_header_content + seperator):]
            yaml_template, yaml_stringset = YamlHandler().parse(
                yaml_header_content
            )
            for openstring in yaml_stringset:
                self._unescape_non_printable(openstring)
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
            # Ignore any string that does not appear in the template,
            # We do this to avoid parsing strings that are not properly
            # handled by the Markdown library, such as ```code``` blocks
            if string and string in md_template[curr_pos:]:
                string_object = OpenString(six.text_type(order),
                                           string,
                                           order=order)
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

    def _is_yaml_string(self, string):
        """Return True if the given open string is in YAML format, False otherwise.

        :param OpenString string: the string object to check
        :return: whether or not the string is in a YAML-formatted block
        :rtype: bool
        """
        # If string's key is of type `int` (e.g. 4), it is a markdown string
        # Strings inside YAML blocks have a string key (e.g. 'root_dict.another_dict')
        try:
            int(string.key)
        except ValueError:
            return True

        return False

    def _escape_invalid_chars(self, openstring):
        """Escape any invalid (non-printable) characters in the given string.

        Modifies the given OpenString object in place, checking strings for all
        plural rules.

        :param OpenString openstring: the string object to check and update
        """
        # Check each plural rule of the string
        for rule, string in six.iteritems(openstring.strings):
            chars = []
            # Go through each character
            # If a control character is found (e.g. backspace)
            # escape it to a unicode format, e.g. \u007f
            for char in string:
                if Reader.NON_PRINTABLE.match(char):
                    chars.append('\\u{:04x}'.format(ord(char)))
                else:
                    chars.append(char)

            openstring._strings[rule] = u"".join(chars)

    def _unescape_non_printable(self, openstring):
        """Unescape any invalid (non-printable) characters in the given string.

        Modifies the given OpenString object in place, checking strings for all
        plural rules.

        :param OpenString openstring: the string object to check and update
        """
        # Check each plural rule of the string
        for rule, string in six.iteritems(openstring.strings):
            # Check \u0000 notation
            all_matches = list(GithubMarkdownHandlerV2.ESCAPED_UNICODE.finditer(string))

            # We need to loop in reverse, otherwise the length of the string
            # changes as we go because of the replacements we do, and the indexes
            # in matches are no longer correct, cutting characters off the string
            # by mistake
            for match in reversed(all_matches):
                escaped = match.group()
                # From a string like '\u0008' get everything after `\u`
                # and convert it to a character based on its int value
                char = six.unichr(int(escaped[2:]))
                if Reader.NON_PRINTABLE.match(char):
                    string = '{before}{repl}{after}'.format(
                        before=string[:match.start()],
                        repl=char,
                        after=string[match.start() + len(escaped):]
                    )

            # Check \x00 notation
            all_matches = list(
                GithubMarkdownHandlerV2.ESCAPED_UNICODE_HEX.finditer(string)
            )

            for match in reversed(all_matches):
                escaped = match.group()
                # From a string like '\x2E' get everything after `\x`
                # and convert it to a character based on its hex int value
                # Exclude \x00, which is non-printable but must not be unescaped,
                # otherwise an exception is thrown when trying to store the string
                # e.g. on the database
                char = six.unichr(int(escaped[2:], 16))
                if Reader.NON_PRINTABLE.match(char) and escaped != '\\x00':
                    string = '{before}{repl}{after}'.format(
                        before=string[:match.start()],
                        repl=char,
                        after=string[match.start() + len(escaped):]
                    )

            openstring._strings[rule] = string

    def _transform_yaml_string(self, openstring):
        """Transform the given YAML-formatted string to make it valid for compilation.

        :param OpenString openstring: the string object to use for the transformation
        :return: a string that is valid for exporting
        :rtype: str
        """
        should_wrap, quote_char = self._should_wrap_in_quotes(openstring)
        if should_wrap:
            string = self._wrap_in_quotes(openstring.string, quote_char)
        else:
            string = openstring.string

        # this is to ensure that if the style is literal or folded
        # http://www.yaml.org/spec/1.2/spec.html#id2795688
        # a new line always follows the string
        if (openstring.flags and openstring.flags[-1] in '|>'):
            string = openstring.flags[-1] + self.NEWLINE + string

        return string

    def _wrap_in_quotes(self, string, quote_char):
        """Wrap the given string in quotes, if necessary.

        :param unicode string: the string to check for wrapping
        :param str quote_char: the character to use for wrapping,
            one of `"` or `'`
        :return: the new string, wrapped in quotes if needed
        :rtype: unicode
        :raise ValueError: if `quote_char` is not one of the valid values
        """
        if quote_char == '"':
            string = string.replace(quote_char, self.BACKSLASH + quote_char)
        elif quote_char == u"'":
            string = string.replace(quote_char, quote_char * 2)
        else:
            raise ValueError(
                'Invalid character ({}) given for wrapping in quotes, '
                'supported values are single quotes (\') '
                'and double quotes (").'.format(quote_char)
            )

        # wrap string with quotes
        return '{}{}{}'.format(quote_char, string, quote_char)

    def _should_wrap_in_quotes(self, openstring):
        """Check if the given string should be wrapped in quotes.

        In order to decide if wrapping is necessary, it takes into account
        various parameters, such as what character the string starts and ends with,
        whether or not it contains special characters, etc.

        :param unicode string: the string to check
        :return: a tuple that shows if wrapping is needed, as well as
            the character that should be used for wrapping
        :rtype: tuple (bool, str)
        """
        # If pipe flag appears do not wrap it.
        if self.PIPE in openstring.flags:
            return False, openstring.flags

        # If single or double quote flags appear, wrap it.
        if openstring.flags in [self.DOUBLE_QUOTES, self.SINGLE_QUOTE]:
            return True, openstring.flags

        string = openstring.string.strip()

        # If wrapped already in double quotes, don't wrap again
        wrapped_in_double_quotes = (
            string.startswith(self.DOUBLE_QUOTES)
            and string.endswith(self.DOUBLE_QUOTES)
        )
        if wrapped_in_double_quotes:
            return False, None

        # If wrapped already in single quotes, don't wrap again
        wrapped_in_single_quotes = (
            string.startswith(self.SINGLE_QUOTE)
            and string.endswith(self.SINGLE_QUOTE)
        )
        if wrapped_in_single_quotes:
            return False, None

        # If starts with a double quote but does not end in a double quote,
        # wrap in single quotes
        should_wrap = (
            string.startswith(self.DOUBLE_QUOTES)
            and not wrapped_in_double_quotes
        )
        if should_wrap:
            return should_wrap, self.SINGLE_QUOTE

        # If starts with a single quote but does not end in a single quote,
        # wrap in double quotes
        should_wrap = (
            string.startswith(self.SINGLE_QUOTE)
            and not wrapped_in_single_quotes
        )
        if should_wrap:
            return should_wrap, self.DOUBLE_QUOTES

        # If needs wrapping due to special characters, wrap in double quotes
        should_wrap = any([
            self.NEWLINE in string[:-1],
            self.COLON in string,
            self.HASHTAG in string,
            string.startswith(self.ASTERISK),
            string.startswith(self.AMPERSAND),
            string.startswith(self.DASH),
            string.startswith(self.AT_SIGN),
            (
                string.startswith(self.BRACKET_LEFT)
                and not string.endswith(self.BRACKET_RIGHT)
            ),
        ])
        if should_wrap:
            return True, self.DOUBLE_QUOTES

        return False, None
