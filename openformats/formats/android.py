from __future__ import absolute_import

import itertools

from ..handlers import Handler
from ..exceptions import ParseError
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from ..utils.xml import NewDumbXml


class AndroidHandler(Handler):
    name = "ANDROID"
    extension = "xml"

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

    def parse(self, content):
        resources_tag_position = content.index(self.PARSE_START)

        self.transcriber = Transcriber(content[resources_tag_position:])
        self.current_comment = None
        self.order_counter = itertools.count()

        source = self.transcriber.source
        parsed = NewDumbXml(source)
        children_itterator = parsed.find_children(
            self.STRING,
            self.STRING_ARRAY,
            self.STRING_PLURAL,
            NewDumbXml.COMMENT
        )
        stringset = []

        for child in children_itterator:
            strings = self._handle_child(child)
            if strings is not None:
                stringset.extend(strings)
                self.current_comment = None

        self.transcriber.copy_until(len(source))
        template = content[:resources_tag_position] +\
            self.transcriber.get_destination()

        return template, stringset

    def _handle_child(self, child):
        """Do basic checks on the child and assigns the appropriate method to
            handle it based on the child's tag.

        :returns: An list of OpenString objects if any were created else None.
        """
        if not self._should_ignore(child):
            if child.tag == self.STRING:
                return self._handle_string(child)
            elif child.tag == self.STRING_ARRAY:
                return self._handle_string_array(child)
            elif child.tag == self.STRING_PLURAL:
                return self._handle_string_plural(child)
            elif child.tag == NewDumbXml.COMMENT:
                self._handle_comment(child)
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
            product
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
        children_itterator = child.find_children(self.STRING_ITEM)
        # Itterate through the children with the item tag.
        for new_child in children_itterator:
            rule = new_child.attrib.get('quantity')
            if rule is None:
                # If quantity is missing the plural is unknown
                raise ParseError(
                    "Missing the `quantity` attribute on line {}".format(
                        self.transcriber.line_number
                    )
                )
            rule_number = self.get_rule_number(rule)
            string_rules_text[rule_number] = new_child.content

        name, product = self._get_child_attributes(child)
        string = self._create_string(
            name,
            string_rules_text,
            self.current_comment,
            product
        )
        if string is not None:
            # <plurals name="foo">   <item>Hello ...
            #                        ^
            first_plural_position = child.text_position + len(child.text)
            self.transcriber.copy_until(first_plural_position)
            self.transcriber.add(string.template_replacement)
            # ...</item>   </plurals>...
            #           ^
            self.transcriber.skip_until(new_child.tail_position)
            # FYI: new_child is the last iterated child from the loop before.
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
        children_itterator = child.find_children(self.STRING_ITEM)
        name, product = self._get_child_attributes(child)
        # Itterate through the children with the item tag.
        for index, new_child in enumerate(children_itterator):
            child_name = u"{}[{}]".format(name, index)
            string = self._create_string(
                child_name,
                new_child.content,
                self.current_comment,
                product
            )

            if string is not None:
                # ... <item>Hello...
                #           ^
                self.transcriber.copy_until(new_child.text_position)

                strings.append(string)
                self.transcriber.add(string.template_replacement)

                # ...ello world</item>...
                #              ^
                self.transcriber.skip(len(new_child.content))
        if strings:
            return strings
        return None

    def _handle_comment(self, child):
        """Will assign the comment found as the current comment."""
        self.current_comment = child.content

    def _create_string(self, name, text, comment, product):
        """Creates a string and returns it. If empty string it returns None.

        :param text: The strings text.
        :param name: The name of the string.
        :param comment: The developer's comment the string might have.
        :param product: Extra context for the string.
        :returns: Returns an OpenString object if the text is not empty
                  else None.
        """
        if self._validate_not_empty:
            # Create OpenString
            string = OpenString(
                name,
                text,
                context=product,
                order=self.order_counter.next(),
                developer_comment=comment
            )
            return string
        return None

    def _validate_not_empty(self, text):
        """Validates that a string is not empty.

        :param text: The string to validate. Can be a basestring or a dict for
                        for pluralized strings.
        :raises: Raises a ParseError if not all plurals of a pluralized string
                 are complete.
        :returns: True if the string is not empty else False.
        """
        # If dict then it's pluralized
        if isinstance(text, dict):
            # If there is plural missing raise error.
            for key, string in text.iteritems():
                if string.strip() == "":
                    raise ParseError(
                        'Missing plural string before the line {}'.format(
                            self.transcriber.line_number
                        )
                    )
        elif text.strip() == "":
            return False
        return True

    def _get_child_attributes(self, child):
        """Retrieves child's `name` and `product` attributes.

        :param child: The child to retrieve the attributes from.
        :returns: Returns a tuple (`name`, `product`)
        :raises: It raises a ParseError if no `name` attribute is present.
        """
        name = child.attrib.get('name')
        if name is None:
            raise ParseError(
                'Missing the `name` attribute on line'.format(
                    self.transcriber.line_number
                )
            )
        product = child.attrib.get('product', '')
        return name, product

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

    """ Compile Methods """

    def compile(self, template, stringset):
        resources_tag_position = template.index(self.PARSE_START)

        self.transcriber = Transcriber(template[resources_tag_position:])
        source = self.transcriber.source

        parsed = NewDumbXml(source)
        children_itterator = parsed.find_children(
            self.STRING,
            self.STRING_ARRAY,
            self.STRING_PLURAL
        )
        # stringset = list(stringset)[:1]
        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()
        print self.next_string
        for child in children_itterator:
            self._compile_child(child)

        self.transcriber.copy_until(len(source))
        compiled = template[:resources_tag_position] +\
            self.transcriber.get_destination()

        return compiled

    def _compile_child(self, child):
        """Do basic checks on the child and assigns the appropriate method to
            handle it based on the child's tag.

        :returns: An list of OpenString objects if any were created else None.
        """
        if not self._should_ignore(child):
            if child.tag == self.STRING:
                return self._compile_string(child)
            elif child.tag == self.STRING_ARRAY:
                return self._compile_string_array(child)
            elif child.tag == self.STRING_PLURAL:
                return self._compile_string_plural(child)
        return False

    def _compile_string(self, child):
        if self._should_compile(child):
            self.transcriber.copy_until(child.text_position)
            self.transcriber.add(self.next_string.string)
            self.transcriber.skip_until(child.content_end)
            self.next_string = self._get_next_string()
        else:
            self._skip_tag(child)

    def _compile_string_array(self, child):
        children_itterator = child.find_children(self.STRING_ITEM)
        for new_child in children_itterator:
            self._compile_string(new_child)

    def _compile_string_plural(self, child):

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
                    )
                    + end
                )
            self.transcriber.skip_until(child.content_end)
            self.next_string = self._get_next_string()
        else:
            self._skip_tag(child)

    def _should_compile(self, child):
        return (
            self.next_string is not None and
            self.next_string.template_replacement == child.content.strip()
        )

    def _skip_tag(self, child):
        self.transcriber.copy_until(child.position)
        self.transcriber.skip_until(child.tail_position)

    def _get_next_string(self):
        try:
            next_string = self.stringset.next()
        except StopIteration:
            next_string = None
        return next_string
