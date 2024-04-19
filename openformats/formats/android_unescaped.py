import re
from hashlib import md5
from openformats.exceptions import ParseError
from openformats.formats.android import AndroidHandler
from ..utils.xml import NewDumbXml as DumbXml
from ..utils.xmlutils import XMLUtils
from ..strings import OpenString


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
        if XMLUtils.validate_not_empty_string(
            self.transcriber,
            text,
            child,
            error_context={"main_tag": "plural", "child_tag": "item"},
        ):
            if (name, product) in self.existing_hashes:
                if child.tag in self.existing_hashes[(name, product)]:
                    format_dict = {"name": name, "child_tag": child.tag}
                    if product:
                        msg = (
                            "Duplicate `tag_name` ({child_tag}) for `name`"
                            " ({name}) and `product` ({product}) "
                            "found on line {line_number}"
                        )
                        format_dict["product"] = product
                    else:
                        msg = (
                            "Duplicate `tag_name` ({child_tag}) for `name`"
                            " ({name}) specify a product to differentiate"
                        )
                    XMLUtils.raise_error(
                        self.transcriber, child, msg, context=format_dict
                    )
                else:
                    product += child.tag
            # Create OpenString
            string = OpenString(
                name,
                text,
                context=product,
                order=next(self.order_counter),
                developer_comment=comment,
                pluralized=pluralized,
            )
            self.existing_hashes.setdefault((name, product), [])
            self.existing_hashes[(name, product)].append(child.tag)
            return string
        return None

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
            r"(?<!\\)@",
            r"(?<!\\)\?",
            r"(?<!\\)\t",
        ]

        for pattern in not_allowed_unescaped:
            if re.search(pattern, protected_string):
                raise ParseError(
                    "You have one or more unescaped characters from the following "
                    f"list ', \", @, ?, \\n, \\t in the string : {text}"
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
            return AndroidHandler.escape(string)

        string = AndroidHandler.escape(string)
        string = (
            string.replace("&", "&amp;")
            .replace(">", "&gt;")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("@", "\\@")
            .replace("?", "\\?")
        )
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
