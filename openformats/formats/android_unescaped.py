import re
from hashlib import md5
from openformats.exceptions import ParseError
from openformats.formats.android import AndroidHandler
from ..utils.xml import NewDumbXml as DumbXml
import six

from __future__ import absolute_import

import itertools
import re

import six

from openformats.exceptions import ParseError
from ..exceptions import RuleError
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.xml import NewDumbXml as DumbXml
from ..utils.xml import escape as xml_escape
from ..utils.xmlutils import XMLUtils, reraise_syntax_as_parse_errors


class AndroidDumbXml(DumbXml):
   
    def _find_next_lt(self, start):
        in_cdata = False
        for ptr in six.moves.xrange(start, len(self.source)):
            candidate = self.source[ptr]
            if in_cdata:
                if (candidate == ']' and
                        self.source[ptr:ptr + len("]]>")] == "]]>"):
                    in_cdata = False
            else:
                if candidate == self.LESS_THAN:
                    # Check against CDATA
                    if self.source[ptr:ptr + len("<![CDATA[")] == "<![CDATA[":
                        # this is the only difference from the parent class,
                        # move the text position to the start of the cdata
                        self._text_position=ptr+len("<![CDATA[")
                        in_cdata = True
                    else:
                        return ptr
        # We reached the end of the string, lets return accordingly
        return len(self.source)
    
    @property
    def content(self):
        """ All the contents of a tag (both text and children tags)
             Parent class:
             <string><![CDATA[goobye <b>cruel</b> world]]></string>
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            
            This class:
            <string><![CDATA[goobye <b>cruel</b> world]]></string>
                             ^^^^^^^^^^^^^^^^^^^^^^^^^
        """

        if self.tag == self.COMMENT:
            return self.text
        if self.content_end is None:
            return None
        _string_value = self.source[self.text_position:self.content_end]
        if _string_value.strip().endswith("]]>"):
            diff = len(_string_value) -len(_string_value.strip())
            self._content_end = self.content_end-diff if diff>0 else self.content_end
            _string_value = self.source[self.text_position:self.content_end-len("]]>")]
        return _string_value


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

class AndroidDumbXml(DumbXml):
    DumbXml = DumbXml
   
    def _find_next_lt(self, start):
        in_cdata = False
        for ptr in six.moves.xrange(start, len(self.source)):
            candidate = self.source[ptr]
            if in_cdata:
                if (candidate == ']' and
                        self.source[ptr:ptr + len("]]>")] == "]]>"):
                    in_cdata = False
            else:
                if candidate == self.LESS_THAN:
                    # Check against CDATA
                    if self.source[ptr:ptr + len("<![CDATA[")] == "<![CDATA[":
                        # this is the only difference from the parent class,
                        # move the text position to the start of the cdata
                        self._text_position=ptr+len("<![CDATA[")
                        in_cdata = True
                    else:
                        return ptr
        # We reached the end of the string, lets return accordingly
        return len(self.source)
    
    @property
    def content(self):
        """ All the contents of a tag (both text and children tags)
             Parent class:
             <string><![CDATA[goobye <b>cruel</b> world]]></string>
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            
            This class:
            <string><![CDATA[goobye <b>cruel</b> world]]></string>
                             ^^^^^^^^^^^^^^^^^^^^^^^^^
        """

        if self.tag == self.COMMENT:
            return self.text
        if self.content_end is None:
            return None
        _string_value = self.source[self.text_position:self.content_end]
        if _string_value.strip().endswith("]]>"):
            diff = len(_string_value) -len(_string_value.strip())
            self._content_end = self.content_end-diff if diff>0 else self.content_end
            _string_value = self.source[self.text_position:self.content_end-len("]]>")]
        return _string_value
    


class AndroidHandler3(AndroidUnescapedHandler):
    PLURAL_TEMPLATE_CDATA = u'<item quantity="{rule}"><![CDATA[{string}]]></item>'
    DumbXml = AndroidDumbXml

    def __init__(self):
        super(AndroidHandler3, self).__init__()
        self.cdata_pattern = re.compile(r'!\[CDATA')

   
    def _handle_string_plural(self, child):
        """Handles child element that has the `plurals` tag.

        It will find children with the `item` tag and create an OpenString
        object out of them.

        :raises: Parse error if the `quantity` attribute is missing from any
                    of the child's children
        :returns: An list containing the OpenString object if one was created
                    else None.
        """

        string_rules_text = {}
        item_iterator = child.find_children()
        # Iterate through the children with the item tag.
        
        try:
            has_cdata = False if self.cdata_pattern.search(child.content) is None else True
        except TypeError:
            raise ParseError("No plurals found in <plurals> tag on line 1")
        
        for item_tag in item_iterator:
            if item_tag.tag != AndroidDumbXml.COMMENT:
                rule_number = self._validate_plural_item(item_tag)
                string_rules_text[rule_number] = item_tag.content

        name, product = self._get_child_attributes(child)
      
        string = self._create_string(
            name,
            string_rules_text,
            self.current_comment,
            product,
            child,
            # <plurals> tags always define plurals, even if the language has
            # one plural form and thus there's only one <item>
            pluralized=True,
        )
      
        if string is not None:
            # <plurals name="foo">   <item>Hello ...
            #                        ^
            first_plural_position = child.text_position + len(child.text or '')
            self.transcriber.copy_until(first_plural_position)
            
            self.transcriber.add(string.template_replacement if not has_cdata else string.template_replacement + "_cdata")
            # ...</item>   </plurals>...
            #           ^
            self.transcriber.skip_until(item_tag.tail_position)
            # FYI: item_tag is the last iterated item from the loop before.
            return [string]
        return None

    

    def _handle_comment(self, child):
        """Will assign the comment found as the current comment."""
        self.current_comment = child.content

    def _create_string(self, name, text, comment, product, child,
                       pluralized=False):
        """Creates a string and returns it. If empty string it returns None.

        :param text: The strings text.
        :param name: The name of the string.
        :param comment: The developer's comment the string might have.
        :param product: Extra context for the string.
        :param child: The child tag that the string is created from.
                        Used to find line numbers when errors occur.
        :returns: Returns an OpenString object if the text is not empty
                  else None.
        """
        if XMLUtils.validate_not_empty_string(
            self.transcriber,
            text,
            child,
            error_context={
                'main_tag': 'plural',
                'child_tag': 'item'
            }
        ):
            if (name, product) in self.existing_hashes:
                if child.tag in self.existing_hashes[(name, product)]:
                    format_dict = {
                        'name': name,
                        'child_tag': child.tag
                    }
                    if product:
                        msg = (
                            u"Duplicate `tag_name` ({child_tag}) for `name`"
                            u" ({name}) and `product` ({product}) "
                            u"found on line {line_number}"
                        )
                        format_dict['product'] = product
                    else:
                        msg = (
                            u"Duplicate `tag_name` ({child_tag}) for `name`"
                            u" ({name}) specify a product to differentiate"
                        )
                    XMLUtils.raise_error(
                        self.transcriber,
                        child,
                        msg,
                        context=format_dict
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
            # TODO Add post processing validation for cdata 
            self.existing_hashes.setdefault((name, product), [])
            self.existing_hashes[(name, product)].append(child.tag)
            return string
        return None

   

 

    """ Compile Methods """

   


    
    def _search_for_cdata(self,_string,_destination):
        """
        The destination list is the entries that the transcriber
        has visited. The last string is the one that is being compiled.
        An example entry is:
        <string name="string_key"><![CDATA[hello]]></string>
        the transcriber will have the following entries:
        [ <string name="string_key"><![CDATA[],
          hello]
        so we need to find if the preceding entry of the 
        actual string is a cdata entry and return True/False
        """
        if not _destination or (len(_destination)> 0 and _destination[-1] != _string):
            return False
        try:
            return bool(self.cdata_pattern.search(_destination[-2]))
        except TypeError:
            return False
        
        
    def _compile_string(self, child):
        """Handles child element that has the `string` and `item` tag.

        It will compile the tag if matching string exists. Otherwise it will
        skip it.
        """
       

        if self._should_compile(child):
           
            self.transcriber.copy_until(child.text_position)
            _string = self.next_string.string
            self.transcriber.add(_string)
           
            has_cdata = self._search_for_cdata(_string, self.transcriber.destination)
            self.transcriber.skip_until(child.content_end if not has_cdata else child.content_end-len("]]>"))
            self.transcriber.copy_until(child.tail_position)
            self.transcriber.mark_section_start()
            self.transcriber.copy_until(child.end)
            self.transcriber.mark_section_end()
            self.next_string = self._get_next_string()
        elif not child.text:
            # In the case of a string-array we don't want to skip an
            # empty array element that was initially empty.
            pass
        else:
            self._skip_tag(child)
       


    def _compile_string_plural(self, child):
        """Handles child element that has the `plurals` tag.

        It will check if pluralized string exists and add every plural as an
        `item` child. If no matching string is found it will remove the tag.

        :NOTE: If the `plurals` had empty `item` tags to begin with we leave
                it as it is.
        """
        # If placeholder (has empty children) skip
        if len(list(child.find_children(self.STRING_ITEM))):
            return
       
        if self._should_compile(child):
            self.transcriber.copy_until(child.text_position)
          
            has_cdata = child.content.strip().endswith("_cdata")
           
            if has_cdata:
                template_replacement = self.next_string.template_replacement+"_cdata"

                splited_content = child.content.split(
                    template_replacement
                )
            else:
                splited_content = child.content.split(
                    self.next_string.template_replacement
                )
            start = splited_content[0]
            end = splited_content[1]
            
            # If newline formating
            if start.startswith(end):
                start = start.replace(end, '', 1)
                self.transcriber.add(end)
            template = self.PLURAL_TEMPLATE_CDATA if  has_cdata else self.PLURAL_TEMPLATE
           
            for rule, string in six.iteritems(self.next_string.string):
                self.transcriber.add(
                    start +
                    template.format(
                        rule=self.get_rule_string(rule), string=string
                    ) + end
                )
            self.transcriber.skip_until(child.content_end)
            self.transcriber.copy_until(child.end)
            self.next_string = self._get_next_string()
        else:
            self._skip_tag(child)

    def _should_compile(self, child):
        """Checks if the current child should be compiled.

        :param child: The child to check if it should be compiled.
        :returns: True if the child should be compiled else False.
        """
        child_content = child.content and child.content.strip() or ''
    
        if child_content.endswith("_cdata"):     
            child_content = child_content.replace("_cdata", "")
       
        return (
            self.next_string is not None and
            self.next_string.template_replacement == child_content
        )
    

    def _skip_tag(self, tag):
        """Skips a tag from the compilation.

        :param tag: The tag to be skipped.
        """
        self.transcriber.skip_until(tag.end)

    def _get_next_string(self):
        """Gets the next string from stringset itterable.

        :returns: An openstring object or None if it has reached the end of
                    the itterable.
        """
        try:
            next_string = next(self.stringset)
        except StopIteration:
            next_string = None
        return next_string

    """ Util Methods """

    @staticmethod
    def _should_ignore(child):
        """Checks if the child contains any key:value pair from the
            SKIP_ATTRIBUTES dict.

        :returns: True if it contains any else false.
        """
        for key, value in six.iteritems(AndroidHandler.SKIP_ATTRIBUTES):
            filter_attr = child.attrib.get(key)
            if filter_attr is not None and filter_attr == value:
                return True
        return False

    # Escaping / Unescaping
    # According to:
    # https://developer.android.com/guide/topics/resources/string-resource#FormattingAndStyling
    # https://developer.android.com/guide/topics/resources/string-resource#StylingWithHTML
    INLINE_TAGS = ("xliff:g", "a", "annotation", "b", "em", "i", "cite", "dfn",
                   "big", "small", "font", "tt", "s", "strike", "del", "u",
                   "sup", "sub", "ul", "li", "br", "div", "span", "p")

    @staticmethod
    def escape(string):
        """ Escape text for use in Android files.

        Respect tags that are allowed in  strings. Examples:
          "hello" world      => \\"hello\\" world
          <a b="c">hello</a> => <a b="c">hello</a>
          <x y="z">hello</x> => <x y=\\"z\\">hello</x>

        :param str string: string to be escaped
        :return: escaped string
        :rtype: unicode
        """

        def _escape_text(string):
            # If the string starts with an at-sign that doesn't identify
            # another string, then we need to escape it using a leading
            # backslash
            if string.startswith(u'@') and not string.startswith(u'@string/'):
                string = string.replace(u'@', u'\\@', 1)
            return string.\
                replace(AndroidDumbXml.DOUBLE_QUOTES,
                        u''.join([AndroidDumbXml.BACKSLASH, AndroidDumbXml.DOUBLE_QUOTES])).\
                replace(AndroidDumbXml.SINGLE_QUOTE,
                        u''.join([AndroidDumbXml.BACKSLASH, AndroidDumbXml.SINGLE_QUOTE]))

        return xml_escape(string, AndroidHandler.INLINE_TAGS, _escape_text)

    @staticmethod
    def unescape(string):
        # If the string starts with an escaped at-sign, do not display the
        # backslash
        if string.startswith(u'\\@'):
            string = string[1:]
        if len(string) and string[0] == string[-1] == AndroidDumbXml.DOUBLE_QUOTES:
            return string[1:-1].\
                replace(u''.join([AndroidDumbXml.BACKSLASH, AndroidDumbXml.DOUBLE_QUOTES]),
                        AndroidDumbXml.DOUBLE_QUOTES)
        else:
            return string.\
                replace(u''.join([AndroidDumbXml.BACKSLASH, AndroidDumbXml.SINGLE_QUOTE]),
                        AndroidDumbXml.SINGLE_QUOTE).\
                replace(u''.join([AndroidDumbXml.BACKSLASH, AndroidDumbXml.DOUBLE_QUOTES]),
                        AndroidDumbXml.DOUBLE_QUOTES)
