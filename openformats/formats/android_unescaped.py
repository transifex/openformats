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
    def escape(string):
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
            string = (
                string.replace("<", "&lt;")
            )
            return string

        string = AndroidHandler.escape(string)
        string = AndroidUnescapedHandler.escape_special_characters(string)
        return AndroidUnescapedHandler._unprotect_inline_tags(string, protected_tags)

    @staticmethod
    def unescape(string):
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
