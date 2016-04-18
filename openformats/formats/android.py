from __future__ import absolute_import

from ..handlers import Handler
from ..exceptions import ParseError
from openformats.exceptions import RuleError
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

    """ Parse Methods """

    def parse(self, content):
        resources_tag_position = content.index(self.PARSE_START)

        self.transcriber = Transcriber(content[resources_tag_position:])
        stringset = []
        self.current_comment = None
        self.order = 0

        source = self.transcriber.source
        parsed = NewDumbXml(source)
        children_itterator = self._get_children_itterator(
            parsed,
            self.STRING,
            self.STRING_ARRAY,
            self.STRING_PLURAL,
            NewDumbXml.COMMENT
        )

        for child in children_itterator:
            strings = self._handle_child(child)
            if strings is not None:
                stringset.extend(strings)
                self.order += len(strings)
                self.current_comment = None

        self.transcriber.copy_until(len(source))
        template = content[:resources_tag_position] +\
            self.transcriber.get_destination()

        return template, stringset

    def _handle_child(self, child):
        """Do basic checks on the child and assigns the appropriate method to
            handle it based on the child's tag.

        :returns: An list of OpenString objects if an were created else None.
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
            self.order,
            self.current_comment,
            product
        )
        if string is not None:
            self.transcriber.copy_until(child.text_position)
            self.transcriber.add(string.template_replacement)
            self.transcriber.skip(len(child.content))
            return [string]
        return None

    def _handle_string_plural(self, child):
        """Handles child element that has the `plurals` tag.

        It will find children with the `item` tag and create an OpenString
        object out of them.

        :raises: Rule error if the `quantity` attribute is missing from any
                    of the child's children
        :returns: An list containing the OpenString object if one was created
                    else None.
        """
        children_itterator = self._get_children_itterator(
            child, self.STRING_ITEM
        )
        string_rules_text = {}
        for new_child in children_itterator:
            rule = new_child.attrib.get('quantity')
            if rule is None:
                raise RuleError("")
            rule_number = self.get_rule_number(rule)
            string_rules_text[rule_number] = new_child.content

        name, product = self._get_child_attributes(child)
        string = self._create_string(
            name,
            string_rules_text,
            self.order,
            self.current_comment,
            product,
            plural=True
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
            return [string]
        return None

    def _handle_string_array(self, child):
        """Handles child element that has the `string-array` tag.

        It will find children with the `item` tag and create an OpenString
        object out of each one of them.

        :returns: An list containing the OpenString objects if any were created
                    else None.
        """
        children_itterator = self._get_children_itterator(
            child, self.STRING_ITEM
        )
        strings = []
        name, product = self._get_child_attributes(child)
        # Itterate through the children with the item tag.
        for index, new_child in enumerate(children_itterator):
            child_name = u"{}[{}]".format(name, index)
            string = self._create_string(
                child_name,
                new_child.content,
                self.order + index,
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

    """ Compile Methods """

    def compile(self, template, stringset):
        resources_tag_position = template.index(self.PARSE_START)
        self.transcriber = Transcriber(template[resources_tag_position:])
        return self.transcriber.source

    @staticmethod
    def _create_string(name, text, order, comment, product, plural=False):
        """Creates a string and returns it. If empty string it returns None.

        :param text: The strings text.
        :param name: The name of the string.
        :param order: The order the string should appear in the file.
        :param comment: The developer's comment the string might have.
        :param product: Extra context for the string.
        :param plural: Flag tha checks if the string is pluralized.
        :returns: Returns an OpenString object if the text is not empty
                  else None.
        :raises: Raises a ParseError if not all plurals of the strings
                 are complete.
        """
        if plural:
            for key, string in text.iteritems():
                if string.strip() == "":
                    raise ParseError(key)
        elif text.strip() == "":
            return None

        string = OpenString(
            name,
            text,
            context=product,
            order=order,
            developer_comment=comment
        )
        return string

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

    @staticmethod
    def _get_child_attributes(child):
        """Retrieves child's `name` and `product` attributes.

        :param child: The child to retrieve the attributes from.
        :returns: Returns a tuple (name, product)
        :raises: It raises a parse error if no `name` attribute is present.
        """
        name = child.attrib.get('name')
        if name is None:
            raise KeyError()
        product = child.attrib.get('product', '')
        return name, product

    @staticmethod
    def _get_children_itterator(dump_xml_object,  *args):
        """Constructs and returns an itterator containing children of
            the dump_xml_object.

        :args: A list of children tags as strings to find and itterate over.
               If None it will contain all the dump_xml_object's children.
        :returns: An itterator containing the dump_xml_object's children.
        """
        return dump_xml_object.find_children(*args)
