from __future__ import absolute_import

import re

from ..handlers import Handler
from ..exceptions import ParseError
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from ..utils.xml import DumbXml, NewDumbXml


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
        self.order = 1

        source = self.transcriber.source
        parsed = NewDumbXml(source)
        children_itterator = self._get_children_itterator(
            parsed,
            *[
                self.STRING,
                self.STRING_ARRAY,
                self.STRING_PLURAL,
                NewDumbXml.COMMENT
            ]
        )

        for child in children_itterator:
            strings = self._handle_child(child)
            if strings:
                stringset.extend(strings)
                self.order += len(strings)
                self.current_comment = None

        self.transcriber.copy_until(len(source))
        template = content[:resources_tag_position] +\
            self.transcriber.get_destination()

        return template, stringset

    def _handle_child(self, child):
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
        name, product = self._get_child_attributes(child)
        string = self._create_string(
            name,
            child.text,
            self.order,
            self.current_comment,
            product
        )
        self.transcriber.copy_until(child.text_position)
        if string is not None:
            self.transcriber.add(string.template_replacement)
            self.transcriber.skip(len(child.text))

        return [string]

    def _handle_string_plural(self, child):
        # <plurals name="foo">   <item>Hello ...
        #                     ^
        self.transcriber.copy_until(child.text_position)

        children_itterator = self._get_children_itterator(
            child, *[self.STRING_ITEM]
        )
        string_rules_text = {}
        for new_child in children_itterator:
            rule = new_child.attrib.get('quantity')
            if rule is None:
                raise ParseError("")
            rule_number = self.get_rule_number(rule)
            string_rules_text[rule_number] = new_child.text

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
            #
            first_plural_position = child.text_position + len(child.text)
            self.transcriber.copy_until(first_plural_position)
            self.transcriber.add(string.template_replacement)
            # ...</item>   </plurals>...
            #           ^
            self.transcriber.skip(
                new_child.tail_position - first_plural_position
            )

        return [string]

    def _handle_string_array(self, child):
        # ...ing-array>|<item>H...
        #              ^
        self.transcriber.copy_until(child.text_position)
        children_itterator = self._get_children_itterator(
            child, *[self.STRING_ITEM]
        )
        strings = []
        name, product = self._get_child_attributes(child)
        for index, new_child in enumerate(children_itterator):
            child_name = u"{}[{}]".format(name, index)
            string = self._create_string(
                child_name,
                new_child.text,
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
                self.transcriber.skip(len(new_child.text))

        return strings

    def _handle_comment(self, child):
        self.current_comment = child.text

    """ Compile Methods """

    def compile(self, template, stringset):
        resources_tag_position = template.index("<resources")
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
                 are completed.
        """
        if plural:
            for string in text.itervalues():
                if string.strip() == "":
                    raise ParseError("")
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
    def _get_child_attributes(child):
        """Retrives child's `name` and `product` attributes.

        :param child: The child to retrieve the attributes from.
        :returns: Returns a tuple (name, product)
        :raises: It raises a parse error if no `name` attribute is present.
        """
        name = child.attrib.get('name')
        if name is None:
            raise ParseError("")
        product = child.attrib.get('product')
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


class OldAndroidHandler(Handler):
    # name = "BETA_ANDROID"
    extension = "xml"

    plural_template = u'<item quantity="{rule}">{string}</item>'
    SPACE_PAT = re.compile(r'^\s*$')
    # Atttibutes that designate a string should be filtered out
    FILTER_ATTRIBUTES = {
        'translatable': 'false'
    }

    EXTRACTS_RAW = False

    def parse(self, content):
        stringset = []
        if type(content) == str:
            content = content.decode("utf-8")  # convert to unicode

        resources_tag_position = content.index("<resources")

        self.transcriber = Transcriber(content[resources_tag_position:])
        source = self.transcriber.source

        self._order = 0

        resources_tag = DumbXml(source)
        last_comment = ""
        for tag, offset in resources_tag.find(("string-array", "string",
                                               "plurals", DumbXml.COMMENT)):
            if self._should_ignore(tag):
                last_comment = ""
                continue
            if tag.name == DumbXml.COMMENT:
                last_comment = tag.inner
                self.transcriber.copy_until(offset + len(tag.content))
            elif tag.name == "string":
                string = self._handle_string_tag(tag, offset, last_comment)
                last_comment = ""
                if string is not None:
                    stringset.append(string)
            elif tag.name == "string-array":
                for string in self._handle_string_array_tag(tag, offset,
                                                            last_comment):
                    if string is not None:
                        stringset.append(string)
                last_comment = ""
            elif tag.name == "plurals":
                string = self._handle_plurals_tag(tag, offset, last_comment)
                if string is not None:
                    stringset.append(string)
                last_comment = ""

        self.transcriber.copy_until(len(source))

        template = content[:resources_tag_position] +\
            self.transcriber.get_destination()

        self.transcriber = None

        return template, stringset

    def _handle_string_tag(self, tag, offset, comment):
        string = None
        if tag.inner.strip() != "":
            context = tag.attrs.get('product', "")
            string = OpenString(tag.attrs['name'], tag.inner,
                                context=context, order=self._order,
                                developer_comment=comment)
            self._order += 1

        # ... <string name="foo">Hello ....
        #                        ^
        self.transcriber.copy_until(offset + tag.inner_offset)

        # ... ing name="foo">Hello world</stri...
        #                               ^
        if string is not None:
            self.transcriber.add(string.template_replacement)
            self.transcriber.skip(len(tag.inner))
        else:
            self.transcriber.copy_until(offset + tag.inner_offset +
                                        len(tag.inner))

        # ...ello World</string>
        #                       ^
        self.transcriber.copy_until(offset + len(tag.content))

        return string

    def _handle_string_array_tag(self, string_array_tag, string_array_offset,
                                 comment):
        # ...ing-array>   <item>H...
        #              ^
        self.transcriber.copy_until(string_array_offset +
                                    string_array_tag.inner_offset)

        context = string_array_tag.attrs.get('product', "")
        for index, (item_tag, item_offset) in enumerate(
                string_array_tag.find('item')):
            string = None
            if item_tag.inner.strip() != "":
                string = OpenString(
                    "{}[{}]".format(string_array_tag.attrs['name'], index),
                    item_tag.inner,
                    context=context,
                    order=self._order,
                    developer_comment=comment
                )
                self._order += 1
                yield string

            # ... <item>Hello...
            #           ^
            self.transcriber.copy_until(string_array_offset + item_offset +
                                        item_tag.inner_offset)

            # ...ello world</item>...
            #              ^
            if string is not None:
                self.transcriber.add(string.template_replacement)
                self.transcriber.skip(len(item_tag.inner))
            else:
                self.transcriber.copy_until(string_array_offset + item_offset +
                                            item_tag.inner_offset)

            # orld</item>   <it...
            #            ^
            self.transcriber.copy_until(
                string_array_offset + item_offset + item_tag.inner_offset +
                len(item_tag.content)
            )

        # </item>  </string-array>
        #                         ^
        self.transcriber.copy_until(string_array_offset +
                                    len(string_array_tag.content))

    def _handle_plurals_tag(self, plurals_tag, plurals_offset, comment):
        # <plurals name="foo">   <item>Hello ...
        #                     ^
        self.transcriber.copy_until(plurals_offset + plurals_tag.inner_offset)

        first_item_offset = None
        strings = {}
        for item_tag, item_offset in plurals_tag.find('item'):
            if item_tag.inner.strip() == "":
                strings = None
                break

            first_item_offset = first_item_offset or item_offset

            rule = self.get_rule_number(item_tag.attrs['quantity'])
            strings[rule] = item_tag.inner
        last_item_tag, last_item_offset = item_tag, item_offset

        if strings is not None:
            context = plurals_tag.attrs.get('product', "")
            string = OpenString(plurals_tag.attrs['name'], strings,
                                pluralized=True,
                                context=context, order=self._order,
                                developer_comment=comment)
            self._order += 1

            # <plurals name="foo">   <item>Hello ...
            #                        ^
            self.transcriber.copy_until(plurals_offset + first_item_offset)

            # ...</item>   </plurals>...
            #           ^
            self.transcriber.add(string.template_replacement)
            self.transcriber.skip(last_item_offset +
                                  len(last_item_tag.content) -
                                  first_item_offset)

        else:
            string = None

        # ...</plurals> ...
        #              ^
        self.transcriber.copy_until(plurals_offset + len(plurals_tag.content))

        return string

    def _should_ignore(self, tag):
        """
        If the tag has a key: value elemement that matches FILTER_ATTRIBUTES
        it will return True, else it returns False
        """
        for key, value in self.FILTER_ATTRIBUTES.iteritems():
            filter_attr = tag.attrs.get(key, None)
            if filter_attr is not None and filter_attr == value:
                return True
        return False

    def compile(self, template, stringset):
        resources_tag_position = template.index("<resources")
        self._stringset = list(stringset)
        self._stringset_index = 0

        self.transcriber = Transcriber(template[resources_tag_position:])
        self.source = self.transcriber.source

        resources_tag = DumbXml(self.source)

        for tag, offset in resources_tag.find(("string", "string-array",
                                               "plurals")):
            if self._should_ignore(tag):
                continue
            if tag.name == "string":
                self._compile_string(tag, offset)
            elif tag.name == "string-array":
                self._compile_string_array(tag, offset)
            elif tag.name == "plurals":
                self._compile_plurals(tag, offset)
        self.transcriber.copy_until(len(self.source))

        # Lets do another pass to clear empty <string-array>s
        self.transcriber = Transcriber(self.transcriber.get_destination())
        self.source = self.transcriber.source
        resources_tag = DumbXml(self.source)
        for string_array_tag, string_array_offset in resources_tag.find(
                "string-array"):
            if (string_array_tag.inner and
                    len(list(string_array_tag.find("item"))) == 0):
                self.transcriber.copy_until(string_array_offset)
                self.transcriber.skip(len(string_array_tag.content))
        self.transcriber.copy_until(len(self.source))

        compiled = template[:resources_tag_position] +\
            self.transcriber.get_destination()

        self._stringset = None
        self._stringset_index = None
        self.transcriber = None

        return compiled

    def _compile_string(self, string_tag, string_offset):
        try:
            next_string = self._stringset[self._stringset_index]
        except IndexError:
            next_string = None
        if (next_string is not None and
                next_string.template_replacement == string_tag.inner):
            # found one to replace
            self._stringset_index += 1

            self.transcriber.copy_until(string_offset +
                                        string_tag.inner_offset)
            self.transcriber.add(next_string.string)
            self.transcriber.skip(len(string_tag.inner))
            self.transcriber.copy_until(string_offset +
                                        len(string_tag.content))

        else:
            # didn't find it, must remove by skipping it
            self.transcriber.copy_until(string_offset)
            self.transcriber.skip(len(string_tag.content))

    def _compile_string_array(self, string_array_tag, string_array_offset):
        self.transcriber.copy_until(string_array_offset +
                                    string_array_tag.inner_offset)
        for item_tag, item_offset in string_array_tag.find("item"):
            try:
                next_string = self._stringset[self._stringset_index]
            except IndexError:
                next_string = None
            if (next_string is not None and
                    next_string.template_replacement == item_tag.inner):
                # found one to replace
                self._stringset_index += 1

                self.transcriber.copy_until(string_array_offset + item_offset +
                                            item_tag.inner_offset)
                self.transcriber.add(next_string.string)
                self.transcriber.skip(len(item_tag.inner))
                self.transcriber.copy_until(string_array_offset + item_offset +
                                            len(item_tag.content))

            else:
                # didn't find it, must remove by skipping it
                self.transcriber.copy_until(string_array_offset + item_offset)
                self.transcriber.skip(len(item_tag.content))
        self.transcriber.copy_until(string_array_offset +
                                    len(string_array_tag.content))

    def _compile_plurals(self, plurals_tag, plurals_offset):
        try:
            next_string = self._stringset[self._stringset_index]
        except IndexError:
            next_string = None
        if (next_string is not None and
                next_string.template_replacement == plurals_tag.inner.strip()):
            # found one to replace, if the hash is on its own on a line with
            # only spaces, we have to remember it's indent
            self._stringset_index += 1

            is_multiline = True
            indent_length = tail_length = 0
            try:
                hash_position = plurals_offset + plurals_tag.inner_offset +\
                    plurals_tag.inner.index(next_string.template_replacement)
                indent_length = self.source[hash_position::-1].\
                    index('\n') - 1
                indent = self.source[hash_position -
                                     indent_length:hash_position]
                end_of_hash = (hash_position +
                               len(next_string.template_replacement))
                tail_length = self.source[end_of_hash:].index('\n')
                tail = self.source[end_of_hash:end_of_hash + tail_length]
            except ValueError:
                is_multiline = False

            is_multiline = (is_multiline and
                            (self.SPACE_PAT.search(indent) and
                             self.SPACE_PAT.search(tail)))

            if is_multiline:
                # write until beginning of hash
                self.transcriber.copy_until(hash_position - indent_length)
                for rule, value in next_string.string.items():
                    self.transcriber.add(
                        indent +
                        self.plural_template.format(
                            rule=self.get_rule_string(rule), string=value
                        ) +
                        tail + '\n'
                    )
                self.transcriber.skip(indent_length +
                                      len(next_string.template_replacement) +
                                      tail_length + 1)

            else:
                # string is not on its own, simply replace hash with all plural
                # forms
                self.transcriber.copy_until(hash_position)
                for rule, value in next_string.string.items():
                    self.transcriber.add(
                        self.plural_template.format(
                            rule=self.get_rule_string(rule), string=value
                        )
                    )
                self.transcriber.skip(indent_length +
                                      len(next_string.template_replacement) +
                                      tail_length)

            # finish up by copying until the end of </plurals>
            self.transcriber.copy_until(plurals_offset +
                                        len(plurals_tag.content))

        else:
            # didn't find it, must remove by skipping it
            self.transcriber.copy_until(plurals_offset)
            self.transcriber.skip_until(plurals_offset +
                                        len(plurals_tag.content))


class NewAndroidHandlers(Handler):
    name = "ANDROID"
    extension = "xml"

    def parse(self, content):
        return content, []
