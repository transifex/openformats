import re
from hashlib import md5
from openformats.exceptions import ParseError
from openformats.formats.android import AndroidHandler
from ..utils.xml import NewDumbXml as DumbXml


class AndroidUnescapedHandler(AndroidHandler):
    def _create_string(self, name, text, comment, product, child, pluralized=False):
        """Creates a string and returns it. If empty string it returns None.
        Also checks if the provided text contains unescaped characters which are
        invalid for the Android XML format.

        :param text: The strings text.
        :param name: The name of the string.
        :param comment: The developer's comment the string might have.
        :param product: Extra context for the string.
        :param child: The child tag that the string is created from.
                        Used to find line numbers when errors occur.
        :returns: Returns an OpenString object if the text is not empty
                    else None.
        """
        AndroidUnescapedHandler._check_unescaped_characters(text)
        return super()._create_string(name, text, comment, product, child, pluralized)

    @staticmethod
    def _check_unescaped_characters(text):
        """Checks if the provided text contains unescaped characters which are
        invalid for the Android XML format.
        """
        if type(text) == dict:
            text = AndroidUnescapedHandler._check_unescaped_characters_in_plural_string(
                text
            )
        else:
            text = AndroidUnescapedHandler._check_unescaped_characters_in_simple_string(
                text
            )

        return text

    @staticmethod
    def _check_unescaped_characters_in_simple_string(text):
        try:
            protected_string, _ = AndroidUnescapedHandler._protect_inline_tags(text)
        except Exception as e:
            raise ParseError(
                "Error escaping the string. Please check for any open tags or any "
                "dangling < characters"
            ) from e

        not_allowed_unescaped = [
            r"(?<!\\)'",
            r'(?<!\\)"',
        ]
        full_pattern = "|".join(not_allowed_unescaped)
        if re.search(full_pattern, protected_string):
            raise ParseError(
                "You have one or more unescaped characters from the following list: ', "
                f'", @, ?, \\n, \\t in the string: {text!r}'
            )

    @staticmethod
    def _check_unescaped_characters_in_plural_string(text):
        for _, string in text.items():
            AndroidUnescapedHandler._check_unescaped_characters_in_simple_string(string)

    @staticmethod
    def _protect_inline_tags(text):
        """Protect INLINE_TAGS from escaping special characters"""
        protected_tags = {}
        wrapped_text = f"<x>{text}</x>"
        parsed = DumbXml(wrapped_text)
        children_iterator = parsed.find_children()

        for child in children_iterator:
            if child.tag in AndroidHandler.INLINE_TAGS:
                child_content = child.source[child.position : child.tail_position]
                string_hash = md5(child_content.encode("utf-8")).hexdigest()
                text = text.replace(child_content, string_hash)
                protected_tags[string_hash] = child_content

        return text, protected_tags

    @staticmethod
    def _unprotect_inline_tags(text, protected_tags):
        for string_hash, string in protected_tags.items():
            text = text.replace(string_hash, string)

        return text

    @staticmethod
    def _process_with_cdata_preservation(text, process_func, is_escape=True):
        """
        Process text while preserving CDATA sections.

        Args:
            text (str): The text to process
            process_func (callable): The processing function to apply to non-CDATA parts
            is_escape (bool): True for escaping, False for unescaping

        Returns:
            str: The processed text with CDATA sections preserved
        """
        if not text or "<![CDATA[" not in text:
            return process_func(text)

        # Pattern to match CDATA sections
        cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"

        # Find all CDATA sections and their positions
        cdata_matches = list(re.finditer(cdata_pattern, text, re.DOTALL))

        if not cdata_matches:
            return process_func(text)

        result = []
        last_end = 0

        for match in cdata_matches:
            # Process the text before the CDATA section
            before_cdata = text[last_end : match.start()]
            if before_cdata:
                result.append(process_func(before_cdata))

            # Keep the CDATA section almost as-is: we escape/unescape single + double
            # quotes to be consistent with current handler behavior (see
            # )
            cdata_content = match.group(0)
            if is_escape:
                cdata_content = cdata_content.replace(
                    DumbXml.DOUBLE_QUOTES,
                    "".join([DumbXml.BACKSLASH, DumbXml.DOUBLE_QUOTES]),
                ).replace(
                    DumbXml.SINGLE_QUOTE,
                    "".join([DumbXml.BACKSLASH, DumbXml.SINGLE_QUOTE]),
                )
            else:
                cdata_content = cdata_content.replace(
                    "".join([DumbXml.BACKSLASH, DumbXml.DOUBLE_QUOTES]),
                    DumbXml.DOUBLE_QUOTES,
                ).replace(
                    "".join([DumbXml.BACKSLASH, DumbXml.SINGLE_QUOTE]),
                    DumbXml.SINGLE_QUOTE,
                )
            result.append(cdata_content)

            last_end = match.end()

        # Process any remaining text after the last CDATA section
        after_cdata = text[last_end:]
        if after_cdata:
            result.append(process_func(after_cdata))

        return "".join(result)

    @staticmethod
    def escape(string):

        def _escape(string):
            try:
                string, protected_tags = AndroidUnescapedHandler._protect_inline_tags(
                    string
                )
            except Exception as _:
                # Exception handling: If an error occurs during tag protection,
                # escape all special characters. One case of these errors is the
                # presence of '<' symbols without corresponding closing tags, causing
                # parsing errors.
                string = AndroidHandler.escape(string)
                string = AndroidUnescapedHandler.escape_special_characters(string)
                string = string.replace("<", "&lt;")
                return string

            string = AndroidHandler.escape(string)
            string = AndroidUnescapedHandler.escape_special_characters(string)
            return AndroidUnescapedHandler._unprotect_inline_tags(
                string, protected_tags
            )

        return AndroidUnescapedHandler._process_with_cdata_preservation(
            string, _escape, is_escape=True
        )

    @staticmethod
    def unescape(string):

        def _unescape(string):
            string = AndroidHandler.unescape(string)
            return (
                string.replace("\\?", "?")
                .replace("\\@", "@")
                .replace("\\t", "\t")
                .replace("\\n", "\n")
                .replace("&gt;", ">")
                .replace("&lt;", "<")
                .replace("&amp;", "&")
            )

        return AndroidUnescapedHandler._process_with_cdata_preservation(
            string, _unescape, is_escape=False
        )

    @staticmethod
    def escape_special_characters(string):
        """
        Escapes special characters in the given string.

        Note:
        - The '<' character is not escaped intentionally to avoid interfering
        with inline tags that need to be protected and unprotected separately.

        :param string: The input string that needs special characters escaped.

        :returns: str: The input string with special characters escaped.
        """
        return (
            string.replace("&", "&amp;")
            .replace(">", "&gt;")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("@", "\\@")
            .replace("?", "\\?")
        )
