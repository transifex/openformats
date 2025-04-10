import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string,
    strip_leading_spaces,
    bytes_to_string,
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
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement

        source_python_template = """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """
        source = source_python_template.format(key=random_key, string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(
            template, source_python_template.format(key=random_key, string=random_hash)
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_string_array(self):
        random_name = generate_random_string()
        random_key = "{}[0]".format(random_name)
        random_string = generate_random_string()
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement
        source_python_template = strip_leading_spaces(
            """
            <resources>
                <string-array name="{key}">
                    <item>{string}</item>
                </string-array>
            </resources>
        """
        )
        source = source_python_template.format(key=random_name, string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(
            template, source_python_template.format(key=random_name, string=random_hash)
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_plurals(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        random_openstring = OpenString(
            random_key, {1: random_singular, 5: random_plural}, order=0
        )
        random_hash = random_openstring.template_replacement

        source = strip_leading_spaces(
            """
            <resources>
                <plurals name="{key}">
                    <item quantity="one">{singular}</item>
                    <item quantity="other">{plural}</item>
                </plurals>
            </resources>
        """.format(
                key=random_key, singular=random_singular, plural=random_plural
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(
            template,
            strip_leading_spaces(
                """
                <resources>
                    <plurals name="{key}">
                        {hash_}
                    </plurals>
                </resources>
            """.format(
                    key=random_key, hash_=random_hash
                )
            ),
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_no_translatable(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string name="{key}" translatable="false">{string}</string>
            </resources>
        """.format(
                key=random_key, string=random_string
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])

        self.assertEqual(stringset, [])
        self.assertEqual(template, source)
        self.assertEqual(compiled, source)

    def test_order_is_kept(self):
        source = """
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
        """
        template, stringset = self.handler.parse(source)
        self.assertEqual(
            [(string.key, string.order) for string in stringset],
            [("a", 0), ("b[0]", 1), ("b[1]", 2), ("c", 3)],
        )

    def test_string_inner_tags_are_collected(self):
        source = """
            <resources>
                <string name="a">hello <b>world</b></string>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "hello <b>world</b>")

    def test_string_content_is_valid_xml(self):
        source = """
            <resources>
                <string name="a">hello <b>world</b></string>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, "hello <b>world</b>")

    def test_string_content_is_not_valid_xml(self):
        self._test_parse_error(
            """
                <resources>
                    <string name="a">hello <b>world</c></string>
                </resources>
            """,
            "Closing tag 'c' does not match opening tag 'b' on line 3",
        )

    def test_empty_string_ignored(self):
        random_key = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string name="{key}"></string>
            </resources>
        """.format(
                key=random_key
            )
        )

        template, stringset = self.handler.parse(source)

        self.assertEqual(stringset, [])
        self.assertEqual(template, source)

    def test_empty_string_array_item_ignored(self):
        random_key = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="{key}">
                    <item></item>
                </string-array>
            </resources>
        """.format(
                key=random_key
            )
        )

        template, stringset = self.handler.parse(source)

        self.assertEqual(stringset, [])
        self.assertEqual(template, source)

    def test_empty_plural_raises_error(self):
        self._test_parse_error(
            '<resources><plurals name="a"></plurals></resources>',
            "No plurals found in <plurals> tag on line 1",
        )

    def test_empty_plural_item_raises_error(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="one"></item>
                        <item quantity="two"></item>
                        <item quantity="other">hello</item>
                    </plurals>
                </resources>
            """,
            ("Missing string(s) in <item> tag(s) in the <plural> tag " "on line 3"),
        )

    def test_all_plural_items_empty_get_skipped(self):
        source = """
            <resources>
                <plurals name="a">
                    <item quantity="one"></item>
                    <item quantity="other"></item>
                </plurals>
            </resources>
        """
        template, stringset = self.handler.parse(source)

        self.assertEqual(template, source)
        self.assertEqual(stringset, [])

    def test_missing_translated_strings_removed(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """.format(
                key=random_key, string=random_string
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
            <resources>
                </resources>
        """
            ),
        )

    def test_missing_translated_string_array_items_removed(self):
        random_key = generate_random_string()
        random_string1 = generate_random_string()
        random_string2 = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="{key}">
                    <item>{string1}</item>
                    <item>{string2}</item>
                </string-array>
            </resources>
        """.format(
                key=random_key, string1=random_string1, string2=random_string2
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [stringset[0]])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
            <resources>
                <string-array name="{key}">
                    <item>{string1}</item>
                </string-array>
            </resources>
        """.format(
                    key=random_key, string1=random_string1
                )
            ),
        )

    def test_missing_translated_plurals_removed(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <plurals name="{key}">
                    <item quantity="one">{singular}</item>
                    <item quantity="other">{plural}</item>
                </plurals>
            </resources>
        """.format(
                key=random_key, singular=random_singular, plural=random_plural
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
            <resources>
                </resources>
        """.format(
                    key=random_key, singular=random_singular, plural=random_plural
                )
            ),
        )

    def test_missing_translated_string_arrays_removed(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="{key}">
                    <item>{string}</item>
                </string-array>
            </resources>
        """.format(
                key=random_key, string=random_string
            )
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
            <resources>
                </resources>
        """
            ),
        )

    def test_compile_plurals_not_indented(self):
        random_key = generate_random_string()
        random_singular = generate_random_string()
        random_plural = generate_random_string()
        random_openstring = OpenString(
            random_key, {1: random_singular, 5: random_plural}, order=0
        )
        source = (
            '<resources><plurals name="{key}"><item quantity="one">'
            '{singular}</item><item quantity="other">{plural}</item>'
            "</plurals></resources>"
        ).format(key=random_key, singular=random_singular, plural=random_plural)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [random_openstring])

        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_missing_quantity_raises_error(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item>a</item>
                        <item quantity="other">b</item>
                    </plurals>
                </resources>
            """,
            "Missing the `quantity` attribute on line 4",
        )

    def test_unknown_quantity(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="one">a</item>
                        <item quantity="three-hundred-and-fifty-four">b</item>
                    </plurals>
                </resources>
            """,
            "The `quantity` attribute on line 5 contains an invalid plural: "
            "`three-hundred-and-fifty-four`",
        )

    def test_missing_other_quantity(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="one">a</item>
                        <item quantity="two">b</item>
                    </plurals>
                </resources>
            """,
            "Quantity 'other' is missing from <plurals> tag on line 3",
        )

    def test_wrong_tag_type_in_plurals_tag(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="other">a</item>
                        <stuff quantity="one">b</stuff>
                    </plurals>
                </resources>
            """,
            (
                "Wrong tag type found on line 5. Was "
                "expecting <item> but found <stuff>"
            ),
        )

    def test_tail_characters_where_they_should_not_be(self):
        self._test_parse_error(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="other">a</item>My tail chars
                        <item quantity="one">b</item>
                    </plurals>
                </resources>
            """,
            "Found trailing characters after <item> tag on line 4",
        )

    def test_duplicate_names(self):
        self._test_parse_error(
            """
                <resources>
                    <string name="a">hello</string>
                    <string name="a">world</string>
                </resources>
            """,
            "Duplicate `tag_name` (string) for `name` (a) specify a"
            " product to differentiate",
        )

    def test_duplicate_names_and_products(self):
        self._test_parse_error(
            """
                <resources>
                    <string name="a" product="b">hello</string>
                    <string name="a" product="b">world</string>
                </resources>
            """,
            "Duplicate `tag_name` (string) for `name` (a) and `product`"
            " (b) found on line 4",
        )

    def test_duplicate_names_and_products_for_different_tag_names(self):
        source = """
             <resources>
                 <plurals name="a" product="b">
                    <item quantity="one">one</item>
                    <item quantity="other">one</item>
                 </plurals>
                 <string name="a" product="b">first string</string>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        string = stringset[0]
        self.assertEqual(string.key, "a")
        self.assertEqual(string.string, {1: "one", 5: "one"})

    def test_name_escaping_helps_with_duplication_cornercases(self):
        source = """s
            <resources>
                <string name="a[0]">hello</string>
                <string-array name="a">
                    <!-- Normally this string would get the name: 'a[0]' which
                         would be identical to the previous one -->
                    <item>goodbye</item>
                </string-array>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        self.assertEqual(stringset[0].key, "a\\[0]")
        self.assertEqual(stringset[1].key, "a[0]")

        source = r"""
            <resources>
                <string name="a[0]">hello</string>
                <!-- If we were only escaping the '[' char, this would still
                     confuse stuff since the item below would get the name:
                     `a\[0]` -->
                <string-array name="a\">
                    <item>goodbye</item>
                </string-array>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        self.assertEqual(stringset[0].key, "a\\[0]")
        self.assertEqual(stringset[1].key, "a\\\\[0]")

    def test_missing_name(self):
        self._test_parse_error(
            "<resources><string>hello</string></resources>",
            "Missing the `name` attribute on line 1",
        )

    def test_missing_first_item_in_array_list(self):
        source = """
            <resources>
              <string-array name="settings_report_a_problem_problem_types">
                  <item>@string/space</item>
                  <item>Installation</item>
                  <item>Bluetooth Connection</item>
                  <item>Technical Troubleshooting</item>
                  <item>How to use Navdy</item>
                  <item>Ordering \u002F Shipping \u002F Payments</item>
                  <item>Other</item>
                  <item>Feedback \u0026 Suggestions</item>
                  <item>Partnership Opportunities</item>
                  <item>Send Logs</item>
              </string-array>
            </resources>
        """
        expected = """
            <resources>
              <string-array name="settings_report_a_problem_problem_types">
                  <item>Installation</item>
                  <item>Bluetooth Connection</item>
                  <item>Technical Troubleshooting</item>
                  <item>How to use Navdy</item>
                  <item>Ordering \u002F Shipping \u002F Payments</item>
                  <item>Other</item>
                  <item>Feedback \u0026 Suggestions</item>
                  <item>Partnership Opportunities</item>
                  <item>Send Logs</item>
              </string-array>
            </resources>
        """
        template, stringset = self.handler.parse(source)
        stringset.pop(0)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, expected)

    def test_compile_removes_missing_strings(self):
        source = strip_leading_spaces(
            """
            <resources>
                <string name="a">hello</string>
                <string name="b">goodbye</string>
            </resources>
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset[:1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    <string name="a">hello</string>
                </resources>
            """
            ),
        )

    def test_compile_removes_missing_string_array_items(self):
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="a">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset[:1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    <string-array name="a">
                        <item>hello</item>
                    </string-array>
                </resources>
            """
            ),
        )

    def test_compile_removes_missing_string_arrays(self):
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="a">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    </resources>
            """
            ),
        )

    def test_compile_doesnt_remove_already_empty_string_array(self):
        source = strip_leading_spaces(
            """
            <resources>
                <string-array name="a"></string-array>
                <string-array name="b">
                    <item>hello</item>
                    <item>world</item>
                </string-array>
            </resources>
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    <string-array name="a"></string-array>
                </resources>
            """
            ),
        )

    def test_compile_removes_missing_plurals(self):
        source = strip_leading_spaces(
            """
            <resources>
                <plurals name="a">
                    <item quantity="one">hello</item>
                    <item quantity="other">world</item>
                </plurals>
            </resources>
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    </resources>
            """
            ),
        )

    def test_compile_doesnt_remove_already_empty_plurals(self):
        source = strip_leading_spaces(
            """
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
        """
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """
                <resources>
                    <plurals name="b">
                        <item quantity="one"></item>
                        <item quantity="other"></item>
                    </plurals>
                </resources>
            """
            ),
        )

    def test_parser_doesnt_like_text_where_it_shouldnt_be(self):
        self._test_parse_error(
            '<resources>hello<string name="a">world</string></resources>',
            "Found leading characters inside <resources> tag on line 1",
        )

    def test_strings_from_plurals_are_always_pluralized(self):
        _, stringset = self.handler.parse(
            """
                <resources>
                    <plurals name="a">
                        <item quantity="other">hello</item>
                    </plurals>
                </resources>
            """
        )
        self.assertTrue(stringset[0].pluralized)

    def test_single_string_skipped(self):
        source = '<resources><string name="a" /></resources>'
        template, stringset = self.handler.parse(source)
        self.assertEqual(source, template)
        self.assertEqual(len(stringset), 0)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_single_string_array_skipped(self):
        source = '<resources><string-array name="a" /></resources>'
        template, stringset = self.handler.parse(source)
        self.assertEqual(source, template)
        self.assertEqual(len(stringset), 0)
        compiled = self.handler.compile(template, stringset)
        self.assertEqual(compiled, source)

    def test_single_string_array_item_skipped(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        random_openstring = OpenString(
            "{}[1]".format(random_key), random_string, order=0
        )
        random_hash = random_openstring.template_replacement

        source_template = """
            <resources>
                <string-array name="{key}">
                    <item />
                    <item>{string}</item>
                </string-array>
            </resources>
        """
        source = source_template.format(key=random_key, string=random_string)

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, stringset)

        self.assertEqual(
            template, source_template.format(key=random_key, string=random_hash)
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(compiled, source)

    def test_single_plural_raises(self):
        self._test_parse_error(
            '<resources><plurals name="a" /></resources>',
            "No plurals found in <plurals> tag on line 1",
        )

    def test_compile_for_target_language_clears_untranslatable_strings(self):
        string = OpenString(generate_random_string(), generate_random_string(), order=0)
        template = """
            <resources>
                <string name="untranslatable"
                        translatable="false">Untranslatable</string>
                <string name="{key}">{string}</string>
            </resources>
        """.format(
            key=string.key, string=string.template_replacement
        )

        # Try for source
        compiled = self.handler.compile(template, [string], is_source=True)
        self.assertEqual(
            compiled,
            """
            <resources>
                <string name="untranslatable"
                        translatable="false">Untranslatable</string>
                <string name="{key}">{string}</string>
            </resources>
        """.format(
                key=string.key, string=string.string
            ),
        )

        # Try for translation
        compiled = self.handler.compile(template, [string], is_source=False)
        self.assertEqual(
            compiled,
            """
            <resources>
                <string name="{key}">{string}</string>
            </resources>
        """.format(
                key=string.key, string=string.string
            ),
        )

    def test_tools_locale(self):
        random_key = generate_random_string()
        random_string = generate_random_string()
        random_openstring = OpenString(random_key, random_string, order=0)
        random_hash = random_openstring.template_replacement

        source_python_template = """
            <resources tools:locale="{language_code}">
                <string name="{key}">{string}</string>
            </resources>
        """
        source = source_python_template.format(
            language_code="en", key=random_key, string=random_string
        )

        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(
            template, [random_openstring], language_info={"code": "fr"}
        )

        self.assertEqual(
            template,
            source_python_template.format(
                language_code="en", key=random_key, string=random_hash
            ),
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].__dict__, random_openstring.__dict__)
        self.assertEqual(
            compiled,
            source_python_template.format(
                language_code="fr", key=random_key, string=random_string
            ),
        )

    def test_escape(self):
        cases = (
            # a"b => a\"b
            (["a", '"', "b"], ["a", "\\", '"', "b"]),
            # a'b => a\'b
            (["a", "'", "b"], ["a", "\\", "'", "b"]),
            # a\b => a\b
            (["a", "\\", "b"], ["a", "\\", "b"]),
            # a\\b => a\\b
            (["a", "\\", "\\", "b"], ["a", "\\", "\\", "b"]),
            # a"b\c => a\"b\c
            (["a", '"', "b", "\\", "c"], ["a", "\\", '"', "b", "\\", "c"]),
            # "a" => \"a\"
            (['"', "a", '"'], ["\\", '"', "a", "\\", '"']),
            # "a"b" => \"\a\"\b\"
            (['"', "a", '"', "b", '"'], ["\\", '"', "a", "\\", '"', "b", "\\", '"']),
            # "a'b" => \"\a\"\b\"
            (['"', "a", "'", "b", '"'], ["\\", '"', "a", "\\", "'", "b", "\\", '"']),
            # Simple
            ('<x y="z">hello</x>', '<x y=\\"z\\">hello</x>'),
            ('<a b="c">"hello"</a>', '<a b="c">\\"hello\\"</a>'),
            # Combined
            (
                '<a b="c">hello</a><x y="z">hello</x>',
                '<a b="c">hello</a><x y=\\"z\\">hello</x>',
            ),
            # Nested
            ('<a b="c"><x y="z">hello</x></a>', '<a b="c"><x y=\\"z\\">hello</x></a>'),
            ('<x y="z"><a b="c">hello</a></x>', '<x y=\\"z\\"><a b="c">hello</a></x>'),
            # Heads and tails
            (
                'this <x y="z">is escaped</x>, this <a b="c">isnt</a>, ok?',
                'this <x y=\\"z\\">is escaped</x>, this <a b="c">isnt</a>, ok?',
            ),
            # Not proper XML
            ('"0 < "1', '\\"0 < \\"1'),
            ('<a>"b"</c>', '<a>\\"b\\"</c>'),
            # Single tags
            ('<a b="c" />', '<a b="c" />'),
            ('<x y="z" />', '<x y=\\"z\\" />'),
            # xliff:g tag
            ('<xliff:g y="z">hello</xliff:g>', '<xliff:g y="z">hello</xliff:g>'),
            # annotation tag
            (
                '<annotation y="z">hello</annotation>',
                '<annotation y="z">hello</annotation>',
            ),
            # At-sign cases
            ("@", "\@"),
            ("@something", "\@something"),
            ('"@enclosed"', '\\"@enclosed\\"'),
            ("no need @", "no need @"),
            # Identifiers should remain intact
            ("@string/one", "@string/one"),
        )
        for rich, raw in cases:
            self.assertEqual(
                AndroidHandler.escape(bytes_to_string(rich)), bytes_to_string(raw)
            )

    def test_unescape(self):
        cases = (
            # a"b => a"b
            (["a", '"', "b"], ["a", '"', "b"]),
            # a'b => a'b
            (["a", "'", "b"], ["a", "'", "b"]),
            # a\b => a\b
            (["a", "\\", "b"], ["a", "\\", "b"]),
            # a\"b => a"b
            (["a", "\\", '"', "b"], ["a", '"', "b"]),
            # a\'b => a'b
            (["a", "\\", "'", "b"], ["a", "'", "b"]),
            # a\\b => a\\b
            (["a", "\\", "\\", "b"], ["a", "\\", "\\", "b"]),
            # "a"b" => a"b
            (['"', "a", '"', "b", '"'], ["a", '"', "b"]),
            # "a'b" => a'b
            (['"', "a", "'", "b", '"'], ["a", "'", "b"]),
            # "a\b" => a\b
            (['"', "a", "\\", "b", '"'], ["a", "\\", "b"]),
            # "a\"b" => a"b
            (['"', "a", "\\", '"', "b", '"'], ["a", '"', "b"]),
            # "a\'b" => a\'b
            (['"', "a", "\\", "'", "b", '"'], ["a", "\\", "'", "b"]),
            # "a\\b" => a\\b
            (['"', "a", "\\", "\\", "b", '"'], ["a", "\\", "\\", "b"]),
            # a"b\c => a"b\c
            (["a", '"', "b", "\\", "c"], ["a", '"', "b", "\\", "c"]),
            # a'b\c => a'b\c
            (["a", "'", "b", "\\", "c"], ["a", "'", "b", "\\", "c"]),
            # a\\"b => a\"b
            (["a", "\\", "\\", '"', "b"], ["a", "\\", '"', "b"]),
            # At-sign cases
            ("\@", "@"),
            ("\@something", "@something"),
            ('\\"@enclosed\\"', '"@enclosed"'),
            ("no need @", "no need @"),
            ("@string/one", "@string/one"),
        )
        for raw, rich in cases:
            self.assertEqual(
                AndroidHandler.unescape(bytes_to_string(raw)), bytes_to_string(rich)
            )
