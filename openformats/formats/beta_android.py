from __future__ import absolute_import

import re

from ..handlers import Handler
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from ..utils.xml import DumbXml


class BetaAndroidHandler(Handler):
    name = "BETA_ANDROID"
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
