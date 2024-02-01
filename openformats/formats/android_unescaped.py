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

        :param text: The strings text.
        :param name: The name of the string.
        :param comment: The developer's comment the string might have.
        :param product: Extra context for the string.
        :param child: The child tag that the string is created from. Used to find
                    line numbers when errors occur.
        :returns: Returns an OpenString object if the text is not empty else None.
        """
        if XMLUtils.validate_not_empty_string(
            self.transcriber,
            text,
            child,
            error_context={"main_tag": "plural", "child_tag": "item"},
        ):
            text = self._escape_quotes(text)
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

    def _escape_quotes(self, text):
        """Allow single and double quotes to be uploaded unescaped but they must be
        returned escaped
        """
        if type(text) == dict:
            text = AndroidUnescapedHandler._escape_quotes_plural_string(text)
        else:
            text = AndroidUnescapedHandler._escape_quotes_simple_string(text)

        return text

    @staticmethod
    def _escape_quotes_simple_string(text):
        text, protected_tags = AndroidUnescapedHandler._protect_inline_tags(text)

        text = re.sub(
            r"(?<!\\)'",
            "".join([DumbXml.BACKSLASH, DumbXml.SINGLE_QUOTE]),
            text,
        )
        text = re.sub(
            r'(?<!\\)"',
            "".join([DumbXml.BACKSLASH, DumbXml.DOUBLE_QUOTES]),
            text,
        )

        text = AndroidUnescapedHandler._unprotect_inline_tags(text, protected_tags)

        return text

    @staticmethod
    def _escape_quotes_plural_string(text):
        escaped_dict = {}
        for key, string in text.items():
            escaped_string = AndroidUnescapedHandler._escape_quotes_simple_string(
                string
            )
            escaped_dict[key] = escaped_string

        return escaped_dict

    @staticmethod
    def _protect_inline_tags(text):
        """Protect INLINE_TAGS from escaping single and double quotes"""
        protected_tags = {}
        wrapped_text = f"<x>{text}</x>"
        parsed = DumbXml(wrapped_text)
        children_iterator = parsed.find_children()

        for child in children_iterator:
            if child.tag in AndroidHandler.INLINE_TAGS:
                child_content = child.source[child.start : child.end]
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
        except Exception as e:
            raise ParseError(
                "Error escaping the string. Please check for any open tags or any "
                "dangling < characters"
            )

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
