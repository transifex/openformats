from __future__ import absolute_import

import re

from ..handler import Handler, String
from ..utils.test import test_handler
from ..utils.xml import DumbXml


class AndroidHandler(Handler):
    name = "Android"

    plural_template = '<item quantity="{rule}">{string}</item>'
    SPACE_PAT = re.compile(r'^\s*$')

    def feed_content(self, content):
        if type(content) == str:
            content = content.decode("utf-8")  # convert to unicode
        self._content = content

        # ... <resources> ...
        #     ^
        opening_position = self._content.index('<resources')
        self.template = self._content[:opening_position]
        self._content = self._content[opening_position:]
        self._template_pointer = 0
        self._order = 0

        document = DumbXml(self._content)
        last_comment = None
        for tag, offset in document.find(('string', 'string-array',
                                          'plurals', DumbXml.COMMENT)):
            if tag.name == DumbXml.COMMENT:
                last_comment = tag.inner
            elif tag.name == "string":
                string = self._handle_string_tag(tag, offset, last_comment)
                last_comment = None
                if string is not None:
                    yield string
            elif tag.name == "string-array":
                for string in self._handle_string_array_tag(tag, offset,
                                                            last_comment):
                    yield string
                last_comment = None
            elif tag.name == "plurals":
                string = self._handle_plurals_tag(tag, offset, last_comment)
                if string is not None:
                    yield string

        # rest of the source file
        self.template += self._content[self._template_pointer:]

        # clean up
        del self._content
        del self._template_pointer
        del self._order

    def _handle_string_tag(self, tag, offset, comment):
        string = None
        if tag.inner.strip() != "":
            string = String(tag.attrs['name'], tag.inner, order=self._order,
                            developer_comment=comment)
            self._order += 1

        # ... <string name="foo">Hello ....
        #                        ^
        end = offset + tag.inner_offset
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

        # ... ing name="foo">Hello world</stri...
        #                               ^
        if string is not None:
            self.template += string.template_replacement
        else:
            self.template += tag.inner
        self._template_pointer += len(tag.inner)

        # ...ello World</string>
        #                      ^
        closing_tag = tag.content[tag.inner_offset + len(tag.inner):]
        self.template += closing_tag
        self._template_pointer += len(closing_tag)

        return string

    def _handle_string_array_tag(self, string_array_tag, string_array_offset,
                                 comment):
        # ...ing-array>   <item>H...
        #              ^
        end = string_array_offset + string_array_tag.inner_offset
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

        for index, (item_tag, item_offset) in enumerate(
                string_array_tag.find('item')):
            string = None
            if item_tag.inner.strip() != "":
                string = String(
                    "{}[{}]".format(string_array_tag.attrs['name'], index),
                    item_tag.inner,
                    order=self._order,
                    developer_comment=comment
                )
                self._order += 1
                yield string

            # ... <item>Hello...
            #           ^
            end = string_array_offset + item_offset + item_tag.inner_offset
            self.template += self._content[self._template_pointer:end]
            self._template_pointer = end

            # ...ello world</item>...
            #              ^
            if string is not None:
                self.template += string.template_replacement
            else:
                self.template += item_tag.inner
            self._template_pointer += len(item_tag.inner)

            # orld</item>   <it...
            #            ^
            closing_tag = item_tag.content[
                item_tag.inner_offset + len(item_tag.inner):
            ]
            self.template += closing_tag
            self._template_pointer += len(closing_tag)

        # </item>  </string-array>
        #                         ^
        end = string_array_offset + len(string_array_tag.content)
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

    def _handle_plurals_tag(self, plurals_tag, plurals_offset, comment):
        end = plurals_offset + plurals_tag.inner_offset
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

        # <plurals name="foo">   <item>Hello ...
        #                     ^
        end = plurals_offset + plurals_tag.inner_offset
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

        first_item_offset = None
        strings = {}
        for item_tag, item_offset in plurals_tag.find('item'):
            if item_tag.inner.strip() == "":
                strings = None
                break

            first_item_offset = first_item_offset or item_offset

            rule = self.RULES_ATOI[item_tag.attrs['quantity']]
            strings[rule] = item_tag.inner
        last_item_tag, last_item_offset = item_tag, item_offset

        if strings is not None:
            string = String(plurals_tag.attrs['name'], strings,
                            order=self._order, developer_comment=comment)
            self._order += 1

            # <plurals name="foo">   <item>Hello ...
            #                        ^
            end = plurals_offset + first_item_offset
            self.template += self._content[self._template_pointer:end]
            self._template_pointer = end

            # ...</item>   </plurals>...
            #           ^
            end = plurals_offset + last_item_offset +\
                len(last_item_tag.content)
            self.template += string.template_replacement
            self._template_pointer = end

        else:
            string = None

        # ...</plurals> ...
        #              ^
        end = plurals_offset + len(plurals_tag.content)
        self.template += self._content[self._template_pointer:end]
        self._template_pointer = end

        return string

    def compile(self, stringset):
        resources_tag_position = self.template.index("<resources")
        self._stringset = stringset
        self._stringset_index = 0
        self._compiled = self.template[:resources_tag_position]
        self._resources_tag_content = self.template[resources_tag_position:]
        self._template_ptr = 0
        resources_tag = DumbXml(self._resources_tag_content)

        for tag, offset in resources_tag.find(("string", "string-array",
                                               "plurals")):
            if tag.name == "string":
                self._compile_string(tag, offset)
            elif tag.name == "string-array":
                self._compile_string_array(tag, offset)
            elif tag.name == "plurals":
                self._compile_plurals(tag, offset)
        self._compiled += self._resources_tag_content[self._template_ptr:]

        # Lets do another pass to clear empty <string-array>s
        self._template = self._compiled
        resources_tag_position = self._template.index("<resources")
        self._compiled = self._template[:resources_tag_position]
        self._resources_tag_content = self._template[resources_tag_position:]
        self._template_ptr = 0
        resources_tag = DumbXml(self._resources_tag_content)
        for string_array_tag, string_array_offset in resources_tag.find(
                "string-array"):
            if len(list(string_array_tag.find("item"))) == 0:
                self._compiled += self._resources_tag_content[
                    self._template_ptr:string_array_offset
                ]
                self._template_ptr = string_array_offset +\
                    len(string_array_tag.content)
        self._compiled += self._resources_tag_content[self._template_ptr:]

        compiled = self._compiled
        del self._stringset
        del self._stringset_index
        del self._compiled
        del self._resources_tag_content
        del self._template_ptr
        return compiled

    def _compile_string(self, string_tag, string_offset):
        try:
            next_string = self._stringset[self._stringset_index]
        except IndexError:
            next_string = None
        if (next_string is not None and
                next_string.template_replacement == string_tag.inner):
            # found one to replace
            end = string_offset + string_tag.inner_offset
            self._compiled += self._resources_tag_content[
                self._template_ptr:end
            ]
            self._compiled += next_string.string
            self._template_ptr = end + len(string_tag.inner)
            self._stringset_index += 1
        else:
            # didn't find it, must remove by having template_ptr skip its
            # contents
            self._compiled += self._resources_tag_content[self._template_ptr:
                                                          string_offset]
            self._template_ptr = string_offset + len(string_tag.content)

    def _compile_string_array(self, string_array_tag, string_array_offset):
        for item_tag, item_offset in string_array_tag.find("item"):
            try:
                next_string = self._stringset[self._stringset_index]
            except IndexError:
                next_string = None
            if (next_string is not None and
                    next_string.template_replacement == item_tag.inner):
                # found one to replace
                end = string_array_offset + item_offset + item_tag.inner_offset
                self._compiled += self._resources_tag_content[
                    self._template_ptr:end
                ]
                self._compiled += next_string.string
                self._template_ptr = end + len(item_tag.inner)
                self._stringset_index += 1
            else:
                # didn't find it, must remove by having template_ptr skip its
                # contents
                self._compiled += self._resources_tag_content[
                    self._template_ptr:item_offset
                ]
                self._template_ptr = item_offset + len(item_tag.content)

    def _compile_plurals(self, plurals_tag, plurals_offset):
        try:
            next_string = self._stringset[self._stringset_index]
        except IndexError:
            next_string = None
        if (next_string is not None and
                next_string.template_replacement == plurals_tag.inner.strip()):
            # found one to replace, if the hash is on its own on a line with
            # only spaces, we have to remember it's indent
            hash_position = plurals_offset + plurals_tag.inner_offset +\
                plurals_tag.inner.index(next_string.template_replacement)
            indent_length = self._resources_tag_content[hash_position::-1].\
                index('\n') - 1
            indent = self._resources_tag_content[hash_position - indent_length:
                                                 hash_position]
            end_of_hash = hash_position + len(next_string.template_replacement)
            tail_length = self._resources_tag_content[end_of_hash:].index('\n')
            tail = self._resources_tag_content[end_of_hash:
                                               end_of_hash + tail_length]

            if (self.SPACE_PAT.search(indent) and self.SPACE_PAT.search(tail)):
                # write until beginning of hash
                self._compiled += self._resources_tag_content[
                    self._template_ptr:hash_position
                ]
                # cut the compiled file back a bit
                self._compiled = self._compiled[:len(self._compiled) -
                                                indent_length]

                for rule, value in next_string.string.items():
                    self._compiled += indent + self.plural_template.format(
                        rule=self.RULES_ITOA[rule], string=value
                    ) + tail + '\n'
                self._template_ptr = hash_position + len(
                    next_string.template_replacement
                ) + tail_length + 1
            else:
                # string is not on its own, simply replace hash with all plural
                # forms
                self._compiled += self._resources_tag_content[
                    self._template_ptr:hash_position
                ]
                for rule, value in next_string.string.items():
                    self._compiled += self.plural_template.format(
                        rule=self.RULES_ITOA[rule], string=value
                    )
                self._template_ptr = hash_position +\
                    len(next_string.template_replacement)

            self._stringset_index += 1
        else:
            # didn't find it, must remove by having template_ptr skip its
            # contents
            self._compiled += self._resources_tag_content[self._template_ptr:
                                                          plurals_offset]
            self._template_ptr = plurals_offset + len(plurals_tag.content)


def main():
    test_handler(AndroidHandler, '''
        <resources>
            <string name="foo1">hello osrld</string>
            <string name="foo2">hello sssfa</string>
            <string name="foo3">hello world</string>
            <string name="foo4">hello sdiid</string>
            <string-array name="asdf">
                <item>asdf</item>
                <item>fdsa</item>
                <item>i883</item>
            </string-array>
            <plurals name="unread_messages">
                <item quantity="one">%s message</item>
                <item quantity="other">%s messages</item>
            </plurals>
        </resources>
    ''')


if __name__ == "__main__":
    main()
