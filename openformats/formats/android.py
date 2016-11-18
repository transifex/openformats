from __future__ import absolute_import

import re
import itertools

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import RuleError
from ..utils.xml import NewDumbXml
from ..transcribers import Transcriber
from ..utils.xmlutils import XMLUtils, reraise_syntax_as_parse_errors


class AndroidHandler(Handler):
    """A handler class that parses and compiles String Resources for ANDROID
    applications. The String Resources file is in XML format.

    String Resources file documentation can be found here:
    http://developer.android.com/guide/topics/resources/string-resource.html
    """

    name = "ANDROID"
    extension = "xml"

    EXTRACTS_RAW = True

    SPECIFIER = re.compile(
        '%((?:(?P<ord>\d+)\$|\((?P<key>\w+)\))?(?P<fullvar>[+#\- 0]*(?:\d+)?'
        '(?:\.\d+)?(hh\|h\|l\|ll|j|z|t|L)?(?P<type>[diufFeEgGxXaAoscpn%])))'
    )

    # Where to start parsing the file
    PARSE_START = "<resources"

    # Relevant tags
    STRING = "string"
    STRING_PLURAL = "plurals"
    STRING_ARRAY = "string-array"

    # Relevant children
    STRING_ITEM = "item"

    # Attributes that if the child contains it should be skipped
    SKIP_ATTRIBUTES = {
        'translatable': 'false'
    }

    # Compile plural template
    PLURAL_TEMPLATE = u'<item quantity="{rule}">{string}</item>'

    """ Parse Methods """

    @reraise_syntax_as_parse_errors
    def parse(self, content, **kwargs):
        self.transcriber = Transcriber(content)
        self.current_comment = u""
        self.order_counter = itertools.count()

        source = self.transcriber.source
        # Skip xml info declaration
        resources_tag_position = source.index(self.PARSE_START)

        parsed = NewDumbXml(source, resources_tag_position)
        XMLUtils.validate_no_text_characters(self.transcriber, parsed)
        XMLUtils.validate_no_tail_characters(self.transcriber, parsed)
        children_itterator = parsed.find_children(
            self.STRING,
            self.STRING_ARRAY,
            self.STRING_PLURAL,
            NewDumbXml.COMMENT
        )
        stringset = []
        self.existing_hashes = {}
        for child in children_itterator:
            strings = self._handle_child(child)
            if strings is not None:
                stringset.extend(strings)
                self.current_comment = u""

        self.transcriber.copy_until(len(source))
        template = self.transcriber.get_destination()

        return template, stringset

    def _handle_child(self, child):
        """Do basic checks on the child and assigns the appropriate method to
            handle it based on the child's tag.

        :returns: An list of OpenString objects if any were created else None.
        """
        XMLUtils.validate_no_tail_characters(self.transcriber, child)
        if not self._should_ignore(child):
            if child.tag == NewDumbXml.COMMENT:
                self._handle_comment(child)
            else:
                if child.tag == self.STRING:
                    return self._handle_string(child)
                elif child.tag == self.STRING_ARRAY:
                    XMLUtils.validate_no_text_characters(
                        self.transcriber, child
                    )
                    return self._handle_string_array(child)
                elif child.tag == self.STRING_PLURAL:
                    XMLUtils.validate_no_text_characters(
                        self.transcriber, child
                    )
                    return self._handle_string_plural(child)
        else:
            self.current_comment = u""
        return None

    def _handle_string(self, child):
        """Handles child element that has the `string` tag.

        If it contains a string it will create an OpenString object.

        :returns: An list of containing the OpenString object
                    if one was created else it returns None.
        """
        name, product = self._get_child_attributes(child)
        string = self._create_string(
            name,
            child.content,
            self.current_comment,
            product,
            child
        )
        if string is not None:
            # <string>My Text</string>
            #         ^
            self.transcriber.copy_until(child.text_position)
            self.transcriber.add(string.template_replacement)
            # <string>My Text</string>
            #                ^
            self.transcriber.skip(len(child.content))
            return [string]
        return None

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
        item_itterator = child.find_children()
        # Itterate through the children with the item tag.
        for item_tag in item_itterator:
            if item_tag.tag != NewDumbXml.COMMENT:
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
            self.transcriber.add(string.template_replacement)
            # ...</item>   </plurals>...
            #           ^
            self.transcriber.skip_until(item_tag.tail_position)
            # FYI: item_tag is the last iterated item from the loop before.
            return [string]
        return None

    def _handle_string_array(self, child):
        """Handles child element that has the `string-array` tag.

        It will find children with the `item` tag and create an OpenString
        object out of each one of them.

        :returns: An list containing the OpenString objects if any were created
                    else None.
        """
        strings = []
        item_itterator = child.find_children(self.STRING_ITEM)
        name, product = self._get_child_attributes(child)
        # Itterate through the children with the item tag.
        for index, item_tag in enumerate(item_itterator):
            XMLUtils.validate_no_tail_characters(self.transcriber, item_tag)
            child_name = u"{}[{}]".format(name, index)
            string = self._create_string(
                child_name,
                item_tag.content,
                self.current_comment,
                product,
                child
            )

            if string is not None:
                # ... <item>Hello...
                #           ^
                self.transcriber.copy_until(item_tag.text_position)

                strings.append(string)
                self.transcriber.add(string.template_replacement)

                # ...ello world</item>...
                #              ^
                self.transcriber.skip(len(item_tag.content))
        if strings:
            return strings
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
                            u" ({name}) spcesify a product to differenciate"
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
                order=self.order_counter.next(),
                developer_comment=comment,
                pluralized=pluralized,
            )
            self.existing_hashes.setdefault((name, product), [])
            self.existing_hashes[(name, product)].append(child.tag)
            return string
        return None

    def _validate_plural_item(self, item_tag):
        """ Performs a number of checks on the plural item to see its validity.

        :param item_tag: The item to perform the checks on.
        :raises: ParseError if the item tag does not meet the requirments.
        :returns: The plural number of the validated item tag.
        """
        if item_tag.tag != self.STRING_ITEM:
            msg = (
                u"Wrong tag type found on line {line_number}. Was "
                u"expecting <item> but found <{wrong_tag}>"
            )
            XMLUtils.raise_error(
                self.transcriber,
                item_tag,
                msg,
                context={'wrong_tag': item_tag.tag}
            )

        XMLUtils.validate_no_tail_characters(self.transcriber, item_tag)

        rule = item_tag.attrib.get('quantity')
        if rule is None:
            # If quantity is missing, the plural is unknown
            msg = u"Missing the `quantity` attribute on line {line_number}"
            XMLUtils.raise_error(
                self.transcriber,
                item_tag,
                msg
            )
        try:
            rule_number = self.get_rule_number(rule)
        except RuleError:
            msg = (
                u"The `quantity` attribute on line {line_number} contains "
                u"an invalid plural: `{rule}`"
            )
            XMLUtils.raise_error(
                self.transcriber,
                item_tag,
                msg,
                context={'rule': rule}
            )
        return rule_number

    def _get_child_attributes(self, child):
        """Retrieves child's `name` and `product` attributes.

        :param child: The child to retrieve the attributes from.
        :returns: Returns a tuple (`name`, `product`)
        :raises: It raises a ParseError if no `name` attribute is present.
        """
        name = child.attrib.get('name')
        if name is None:
            msg = u'Missing the `name` attribute on line {line_number}'
            XMLUtils.raise_error(
                self.transcriber,
                child,
                msg
            )
        name = name.replace('\\', '\\\\').replace('[', '\\[')
        product = child.attrib.get('product', '')
        return name, product

    """ Compile Methods """

    def compile(self, template, stringset):
        resources_tag_position = template.index(self.PARSE_START)

        self.transcriber = Transcriber(template[resources_tag_position:])
        source = self.transcriber.source

        parsed = NewDumbXml(source)
        # This is needed in case the first tag is skipped to retain
        # the file's formating
        first_tag_position = parsed.text_position + len(parsed.text)
        self.transcriber.copy_until(first_tag_position)

        children_itterator = parsed.find_children(
            self.STRING,
            self.STRING_ARRAY,
            self.STRING_PLURAL
        )

        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()
        for child in children_itterator:
            self._compile_child(child)

        self.transcriber.copy_until(len(source))
        compiled = template[:resources_tag_position] +\
            self.transcriber.get_destination()

        return compiled

    def _compile_child(self, child):
        """Do basic checks on the child and assigns the appropriate method to
            handle it based on the child's tag.
        """

        if not self._should_ignore(child):
            if child.tag == self.STRING:
                self._compile_string(child)
            elif child.tag == self.STRING_ARRAY:
                self._compile_string_array(child)
            elif child.tag == self.STRING_PLURAL:
                self._compile_string_plural(child)
        else:
            self.transcriber.copy_until(child.end)

    def _compile_string(self, child):
        """Handles child element that has the `string` and `item` tag.

        It will compile the tag if matching string exists. Otherwise it will
        skip it.
        """
        if self._should_compile(child):
            self.transcriber.copy_until(child.text_position)
            self.transcriber.add(self.next_string.string)
            self.transcriber.skip_until(child.content_end)
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

    def _compile_string_array(self, child):
        """Handles child element that has the `string-array` tag.

        It will find children with the `item` tag that should be compiled and
        will compile them. If no matching string is found for a child it will
        remove it. If the `string-array` tag will be empty after compilation
        it will remove it as well.

        :NOTE: If the `string-array` was empty to begin with it will leave it
                as it is.
        """
        item_itterator = list(child.find_children(self.STRING_ITEM))

        # If placeholder (has no children) skip
        if len(item_itterator) == 0:
            self.transcriber.copy_until(child.end)
            return

        # Check if any string matches array items
        has_match = False
        for item_tag in item_itterator:
            if self._should_compile(item_tag):
                has_match = True
                break

        if has_match:
            # Compile found item nodes. Remove the rest.
            for item_tag in item_itterator:
                self._compile_string(item_tag)
            self.transcriber.remove_section()
            self.transcriber.add(item_itterator[-1].tail)
            self.transcriber.copy_until(child.end)
        else:
            # Remove the `string-array` tag
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

            splited_content = child.content.split(
                self.next_string.template_replacement
            )
            start = splited_content[0]
            end = splited_content[1]

            # If newline formating
            if start.startswith(end):
                start = start.replace(end, '', 1)
                self.transcriber.add(end)

            for rule, string in self.next_string.string.items():
                self.transcriber.add(
                    start +
                    self.PLURAL_TEMPLATE.format(
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
            next_string = self.stringset.next()
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
        for key, value in AndroidHandler.SKIP_ATTRIBUTES.iteritems():
            filter_attr = child.attrib.get(key)
            if filter_attr is not None and filter_attr == value:
                return True
        return False

    # Escaping / Unescaping
    # According to:
    # http://developer.android.com/guide/topics/resources/string-resource.html#FormattingAndStyling  # noqa

    @staticmethod
    def escape(string):
        return string.replace('\\', '\\\\').replace('"', '\\"').\
            replace("'", "\\'")

    @staticmethod
    def unescape(string):
        if len(string) and string[0] == string[-1] == '"':
            return string[1:-1]
        else:
            return string.replace('\\"', '"').replace("\\'", "'").\
                replace('\\\\', '\\')
