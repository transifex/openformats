import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string, strip_leading_spaces
)

from openformats.formats.android import AndroidHandler


class AndroidTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = AndroidHandler
    TESTFILE_BASE = "openformats/tests/formats/android/files"

    def setUp(self):
        super(AndroidTestCase, self).setUp()
        self.handler = AndroidHandler()

    def test_string(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        random_openstring = OpenString(random_key,
                                       random_string, order=0)
        random_hash = random_openstring.template_replacement

        source_python_template = u'''
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        '''
        source = source_python_template.format(key=random_key,
                                               string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            source_python_template.format(key=random_key, string=random_hash)
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_string_array(self):
        random_name = generate_random_string()
        random_key = '{}[0]'.format(random_name)
        random_string = generate_random_string()
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement
        source_python_template = strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item>{string}</item>
                </string-array>
            </resources>
        ''')
        source = source_python_template.format(key=random_name,
                                               string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            source_python_template.format(key=random_name, string=random_hash)
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__,
                          random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_plurals(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        random_openstring = OpenString(random_key,
                                       {1: random_singular, 5: random_plural},
                                       order=0)
        random_hash = random_openstring.template_replacement

        source = strip_leading_spaces(u"""
            <resources>
                <plurals name="{key}">
                    <item quantity="one">{singular}</item>
                    <item quantity="other">{plural}</item>
                </plurals>
            </resources>
        """.format(key=random_key, singular=random_singular,
                   plural=random_plural))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(
            template,
            strip_leading_spaces(u'''
                <resources>
                    <plurals name="{key}">
                        {hash_}
                    </plurals>
                </resources>
            '''.format(key=random_key, hash_=random_hash))
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_no_translatable(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string name="{key}" translatable="false">{string}</string>
            </resources>
        '''.format(key=random_key, string=random_string))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])

        self.assertEquals(stringset, [])
        self.assertEquals(template, source)
        self.assertEquals(compiled, source)

    def test_order_is_kept(self):
        source = '''
            <resources>
                <string name="a">a</string>
                <string-array name="b">
                    <item>b</item>
                    <item>c</item>
                </string-array>
                <plurals name="c">
                    <item quantity="one">d</item>
                    <item quantity="other">e</item>
                </plurals>
            </resources>
        '''
        template, stringset = self.handler.parse(source)
        self.assertEquals([(string.key, string.order) for string in stringset],
                          [('a', 0), ('b[0]', 1), ('b[1]', 2), ('c', 3)])

    def test_string_inner_tags_are_collected(self):
        source = '''
            <resources>
                <string name="a">hello <b>world</b></string>
            </resources>
        '''
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEquals(string.key, 'a')
        self.assertEquals(string.string, "hello <b>world</b>")

    def test_string_content_is_valid_xml(self):
        source = '''
            <resources>
                <string name="a">hello <b>world</b></string>
            </resources>
        '''
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEquals(string.key, 'a')
        self.assertEquals(string.string, "hello <b>world</b>")

    def test_string_content_is_not_valid_xml(self):
        self._test_parse_error(
            '''
                <resources>
                    <string name="a">hello <b>world</c></string>
                </resources>
            ''',
            "Closing tag 'c' does not match opening tag 'b' on line 3"
        )

    def test_empty_string_ignored(self):
        random_key = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string name="{key}"></string>
            </resources>
        '''.format(key=random_key))

        template, stringset = self.handler.parse(source)

        self.assertEquals(stringset, [])
        self.assertEquals(template, source)

    def test_empty_string_array_item_ignored(self):
        random_key = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item></item>
                </string-array>
            </resources>
        '''.format(key=random_key))

        template, stringset = self.handler.parse(source)

        self.assertEquals(stringset, [])
        self.assertEquals(template, source)

    def test_empty_plural_raises_error(self):
        self._test_parse_error(
            '<resources><plurals name="a"></plurals></resources>',
            u"Empty <plurals> tag on line 1"
        )

    def test_empty_plural_item_raises_error(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item quantity="one"></item>
                        <item quantity="two"></item>
                        <item quantity="other">hello</item>
                    </plurals>
                </resources>
            ''',
            (
                'Missing string(s) in <item> tag(s) in the <plural> tag '
                'on line 3'
            )
        )

    def test_all_plural_items_empty_get_skipped(self):
        source = u'''
            <resources>
                <plurals name="a">
                    <item quantity="one"></item>
                    <item quantity="other"></item>
                </plurals>
            </resources>
        '''
        template, stringset = self.handler.parse(source)

        self.assertEquals(template, source)
        self.assertEquals(stringset, [])

    def test_missing_translated_strings_removed(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        '''.format(key=random_key, string=random_string))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, strip_leading_spaces(u'''
            <resources>

            </resources>
        '''))

    def test_missing_translated_string_array_items_removed(self):
        random_key = generate_random_string()
        random_string1 = generate_random_string()
        random_string2 = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item>{string1}</item>
                    <item>{string2}</item>
                </string-array>
            </resources>
        '''.format(key=random_key, string1=random_string1,
                   string2=random_string2))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [stringset[0]])
        self.assertEquals(compiled, strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item>{string1}</item>

                </string-array>
            </resources>
        '''.format(key=random_key, string1=random_string1)))

    def test_missing_translated_plurals_removed(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <plurals name="{key}">
                    <item quantity="one">{singular}</item>
                    <item quantity="other">{plural}</item>
                </plurals>
            </resources>
        '''.format(key=random_key, singular=random_singular,
                   plural=random_plural))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, strip_leading_spaces(u'''
            <resources>

            </resources>
        '''.format(key=random_key, singular=random_singular,
                   plural=random_plural)))

    def test_missing_translated_string_arrays_removed(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(u'''
            <resources>
                <string-array name="{key}">
                    <item>{string}</item>
                </string-array>
            </resources>
        '''.format(key=random_key, string=random_string))

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, strip_leading_spaces(u'''
            <resources>

            </resources>
        '''))

    def test_compile_plurals_not_indented(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        random_openstring = OpenString(random_key,
                                       {1: random_singular, 5: random_plural},
                                       order=0)
        source = (u'<resources><plurals name="{key}"><item quantity="one">'
                  '{singular}</item><item quantity="other">{plural}</item>'
                  '</plurals></resources>').format(key=random_key,
                                                   singular=random_singular,
                                                   plural=random_plural)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEquals(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_missing_quantity_raises_error(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item>a</item>
                        <item quantity="other">b</item>
                    </plurals>
                </resources>
            ''',
            u"Missing the `quantity` attribute on line 4"
        )

    def test_unknown_quantity(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item quantity="one">a</item>
                        <item quantity="three-hundred-and-fifty-four">b</item>
                    </plurals>
                </resources>
            ''',
            u"The `quantity` attribute on line 5 contains an invalid plural: "
            u"`three-hundred-and-fifty-four`"
        )

    def test_missing_other_quantity(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item quantity="one">a</item>
                        <item quantity="two">b</item>
                    </plurals>
                </resources>
            ''',
            u"Quantity 'other' is missing from <plurals> tag on line 3"
        )

    def test_wrong_tag_type_in_plurals_tag(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item quantity="other">a</item>
                        <stuff quantity="one">b</stuff>
                    </plurals>
                </resources>
            ''',
            (
                u"Wrong tag type found on line 5. Was "
                u"expecting <item> but found <stuff>"
            )
        )

    def test_tail_characters_where_they_should_not_be(self):
        self._test_parse_error(
            '''
                <resources>
                    <plurals name="a">
                        <item quantity="other">a</item>My tail chars
                        <item quantity="one">b</item>
                    </plurals>
                </resources>
            ''',
            u"Found trailing characters after 'item' tag on line 4"
        )

    def test_duplicate_names(self):
        self._test_parse_error(
            '''
                <resources>
                    <string name="a">hello</string>
                    <string name="a">world</string>
                </resources>
            ''',
            u"Duplicate `name` (a) attribute found on line 4. Specify a "
            "`product` to differentiate"
        )

    def test_duplicate_names_and_products(self):
        self._test_parse_error(
            '''
                <resources>
                    <string name="a" product="b">hello</string>
                    <string name="a" product="b">>world</string>
                </resources>
            ''',
            u"Duplicate `name` (a) and `product` (b) attributes found on line "
            u"4"
        )

    def test_name_escaping_helps_with_duplication_cornercases(self):
        source = '''
            <resources>
                <string name="a[0]">hello</string>
                <string-array name="a">
                    <!-- Normally this string would get the name: 'a[0]' which
                         would be identical to the previous one -->
                    <item>goodbye</item>
                </string-array>
            </resources>
        '''
        template, stringset = self.handler.parse(source)
        self.assertEquals(stringset[0].key, "a\\[0]")
        self.assertEquals(stringset[1].key, "a[0]")

        source = r'''
            <resources>
                <string name="a[0]">hello</string>
                <!-- If we were only escaping the '[' char, this would still
                     confuse stuff since the item below would get the name:
                     `a\[0]` -->
                <string-array name="a\">
                    <item>goodbye</item>
                </string-array>
            </resources>
        '''
        template, stringset = self.handler.parse(source)
        self.assertEquals(stringset[0].key, "a\\[0]")
        self.assertEquals(stringset[1].key, "a\\\\[0]")

    def test_missing_name(self):
        self._test_parse_error('<resources><string>hello</string></resources>',
                               u"Missing the `name` attribute on line 1")

    def test_compile_removes_missing_strings(self):
        source = strip_leading_spaces('''
            <resources>
                <string name="a">hello</string>
                <string name="b">goodbye</string>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset[:1])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>
                    <string name="a">hello</string>

                </resources>
            ''')
        )

    def test_compile_removes_missing_string_array_items(self):
        source = strip_leading_spaces('''
            <resources>
                <string-array name="a">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset[:1])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>
                    <string-array name="a">
                        <item>hello</item>

                    </string-array>
                </resources>
            ''')
        )

    def test_compile_removes_missing_string_arrays(self):
        source = strip_leading_spaces('''
            <resources>
                <string-array name="a">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>

                </resources>
            ''')
        )

    def test_compile_doesnt_remove_already_empty_string_array(self):
        source = strip_leading_spaces('''
            <resources>
                <string-array name="a"></string-array>
                <string-array name="b">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>
                    <string-array name="a"></string-array>

                </resources>
            ''')
        )

    def test_compile_removes_missing_plurals(self):
        source = strip_leading_spaces('''
            <resources>
                <plurals name="a">
                    <item quantity="one">hello</item>
                    <item quantity="other">world</item>
                </plurals>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>

                </resources>
            ''')
        )

    def test_compile_doesnt_remove_already_empty_plurals(self):
        source = strip_leading_spaces('''
            <resources>
                <plurals name="a">
                    <item quantity="one">hello</item>
                    <item quantity="other">world</item>
                </plurals>
                <plurals name="b">
                    <item quantity="one"></item>
                    <item quantity="other"></item>
                </plurals>
            </resources>
        ''')
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(
            compiled,
            strip_leading_spaces('''
                <resources>

                    <plurals name="b">
                        <item quantity="one"></item>
                        <item quantity="other"></item>
                    </plurals>
                </resources>
            ''')
        )

    def test_parser_doesnt_like_text_where_it_shouldnt_be(self):
        self._test_parse_error(
            u'<resources>hello<string name="a">world</string></resources>',
            u"Found leading characters inside 'resources' tag on line 1"
        )

    def test_strings_from_plurals_are_always_pluralized(self):
        _, stringset = self.handler.parse(
            u'''
                <resources>
                    <plurals name="a">
                        <item quantity="other">hello</item>
                    </plurals>
                </resources>
            '''
        )
        self.assertTrue(stringset[0].pluralized)

    def test_escape(self):
        cases = (('double " quote', 'double \\" quote'),
                 ("single ' quote", "single \\' quote"),
                 ("back \\ slash", "back \\\\ slash"))
        for rich, raw in cases:
            self.assertEquals(AndroidHandler.escape(rich), raw)

    def test_unescape(self):
        cases = (('double " quote', 'double \\" quote'),
                 ("single ' quote", "single \\' quote"),
                 ("back \\ slash", "back \\\\ slash"),
                 ('inside double quotes', '"inside double quotes"'),
                 ("single ' quote", '"single \' quote"'),
                 ("back \\ slash", '"back \\ slash"'))
        for rich, raw in cases:
            self.assertEquals(AndroidHandler.unescape(raw), rich)
