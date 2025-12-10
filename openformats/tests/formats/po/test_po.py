import unittest
import itertools
import polib

from openformats.exceptions import ParseError
from openformats.formats.po import PoHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import strip_leading_spaces, generate_random_string


class PoTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = PoHandler
    TESTFILE_BASE = "openformats/tests/formats/po/files"

    def setUp(self):
        super(PoTestCase, self).setUp()
        self.handler = PoHandler()
        self.order_generator = itertools.count()

    def _create_openstring(self, pluralized, extra_context=None):
        context_dict = extra_context if extra_context is not None else {}
        context_dict.update(
            {"order": next(self.order_generator), "pluralized": pluralized}
        )
        key = generate_random_string()
        if pluralized:
            key = ":".join([key, generate_random_string()])

        openstring = OpenString(
            key,
            {0: generate_random_string(), 1: generate_random_string()}
            if pluralized
            else generate_random_string(),
            **context_dict
        )
        openstring.string_hash
        return openstring

    def test_openstring_has_all_fields(self):
        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
            "Language: en\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\n"

            #  translator-comments1
            #  translator-comments2
            #. extracted-comments1
            #. extracted-comments2
            #: validators.py:9
            #: validators.py:11
            #, python-format
            #, another-flag
            msgid "metest"
            msgstr "msgstr1"
        """
        )
        template, stringset = self.handler.parse(source)
        expected_comment = (
            "extracted-comments1\nextracted-comments2\n"
            " translator-comments1\n translator-comments2"
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].developer_comment, expected_comment)
        self.assertEqual(stringset[0].occurrences, "validators.py:9, validators.py:11")
        self.assertEqual(stringset[0].flags, "python-format, another-flag")

    def test_compiled_includes_all_with_obsoleted_strings(self):
        """
        Test that the existence of obsoleted strings in the po file
        marked with #~ does not cause strings after the obsoleted ones
        to be missing from the compiled file.
        """
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False)
        string3 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            #~ msgid "{s2_key}"
            #~ msgstr "{s2_str}"

            msgid "{s3_key}"
            msgstr "{s3_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                    "s3_key": string3.key,
                    "s3_str": string3.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1, string2, string3])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"

                #~ msgid "{s2_key}"
                #~ msgstr "{s2_str}"

                msgid "{s3_key}"
                msgstr "{s3_str}"
                """.format(
                    **{
                        "s1_key": string1.key,
                        "s1_str": string1.string,
                        "s2_key": string2.key,
                        "s2_str": string2.string,
                        "s3_key": string3.key,
                        "s3_str": string3.string,
                    }
                )
            ),
        )

    def test_removes_untranslated_non_pluralized(self):
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False)
        string3 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            msgid "{s2_key}"
            msgstr "{s2_str}"

            msgid "{s3_key}"
            msgstr "{s3_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                    "s3_key": string3.key,
                    "s3_str": string3.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        template = self.handler.sync_template(template, [string1, string3])
        compiled = self.handler.compile(template, [string1, string3])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"

                msgid "{s3_key}"
                msgstr "{s3_str}"
                """.format(
                    **{
                        "s1_key": string1.key,
                        "s1_str": string1.string,
                        "s3_key": string3.key,
                        "s3_str": string3.string,
                    }
                )
            ),
        )

    def test_removes_untranslated_pluralized(self):
        string1 = self._create_openstring(True)
        keys1 = string1.key.split(":")
        string2 = self._create_openstring(True)
        keys2 = string2.key.split(":")
        string3 = self._create_openstring(True)
        keys3 = string3.key.split(":")
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgid_plural "{s1_key_plural}"
            msgstr[0] "{s1_str_singular}"
            msgstr[1] "{s1_str_plural}"

            msgid "{s2_key}"
            msgid_plural "{s2_key_plural}"
            msgstr[0] "{s2_str_singular}"
            msgstr[1] "{s2_str_plural}"

            msgid "{s3_key}"
            msgid_plural "{s3_key_plural}"
            msgstr[0] "{s3_str_singular}"
            msgstr[1] "{s3_str_plural}"
        """.format(
                **{
                    "s1_key": keys1[0],
                    "s1_key_plural": keys1[1],
                    "s1_str_singular": string1.string[0],
                    "s1_str_plural": string1.string[1],
                    "s2_key": keys2[0],
                    "s2_key_plural": keys2[1],
                    "s2_str_singular": string2.string[0],
                    "s2_str_plural": string2.string[1],
                    "s3_key": keys3[0],
                    "s3_key_plural": keys3[1],
                    "s3_str_singular": string3.string[0],
                    "s3_str_plural": string3.string[1],
                }
            )
        )
        template, stringset = self.handler.parse(source)
        template = self.handler.sync_template(template, [string1, string3])
        compiled = self.handler.compile(template, [string1, string3])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgid_plural "{s1_key_plural}"
                msgstr[0] "{s1_str_singular}"
                msgstr[1] "{s1_str_plural}"

                msgid "{s3_key}"
                msgid_plural "{s3_key_plural}"
                msgstr[0] "{s3_str_singular}"
                msgstr[1] "{s3_str_plural}"
                """.format(
                    **{
                        "s1_key": keys1[0],
                        "s1_key_plural": keys1[1],
                        "s1_str_singular": string1.string[0],
                        "s1_str_plural": string1.string[1],
                        "s3_key": keys3[0],
                        "s3_key_plural": keys3[1],
                        "s3_str_singular": string3.string[0],
                        "s3_str_plural": string3.string[1],
                    }
                )
            ),
        )

    def test_not_source_removes_untranslated_on_upload(self):
        string1 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            msgid "a_random_key"
            msgstr " "
        """.format(
                **{"s1_key": string1.key, "s1_str": string1.string}
            )
        )
        template, stringset = self.handler.parse(source)
        template = self.handler.sync_template(template, [string1])
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"
                """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_duplicated_text_is_not_confused(self):
        string1 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            msgctxt ""
            msgid "{s1_key}"
            msgstr "{s1_key}"

            msgctxt "t2"
            msgid "{s1_key}"
            msgstr "{s1_key}"
        """.format(
                **{
                    "s1_key": string1.key,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        template = self.handler.sync_template(template, [string1])
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgctxt ""
                msgid "{s1_key}"
                msgstr "{s1_str}"
            """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_fuzzy_flag_removes_entry_but_keeps_strings(self):
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False, extra_context={"fuzzy": True})
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            #, fuzzy
            msgid "{s2_key}"
            msgstr "{s2_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"
                """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_only_keys_error(self):
        self._test_parse_error(
            """
            msgid "msgid1"
            msgstr ""

            msgid "msgid2"
            msgstr "msgstr2"
            """,
            "A non-empty msgstr was found on the entry with msgid 'msgid2'. Remove and "
            "try again",
            parse_kwargs={"is_source": True},
        )

        self._test_parse_error(
            """
            msgid "msgid1"
            msgid_plural "msgid_plural1"
            msgstr[0] ""
            msgstr[1] ""

            msgid "msgid2"
            msgstr "msgstr2"
            """,
            "A non-empty msgstr was found on the entry with msgid 'msgid2'. Remove and "
            "try again",
            parse_kwargs={"is_source": True},
        )

    def test_only_values_error(self):
        self._test_parse_error(
            """
            msgid "msgid1"
            msgstr "msgstr1"

            msgid "msgid2"
            msgstr ""
            """,
            "The entry with msgid 'msgid2' includes an empty msgstr. Provide a value "
            "and try again",
            parse_kwargs={"is_source": True},
        )

    def test_msgstr_in_plural_entry(self):
        self._test_parse_error(
            """
            msgid "p1"
            msgid_plural "p2"
            msgstr "msgstr"
            """,
            "An unexpected msgstr was found on the pluralized entry with "
            "msgid 'p1' and msgid_plural 'p2'",
        )

    def test_pluralized_msgstr_in_non_pluralized_entry(self):
        self._test_parse_error(
            """
            msgid "p1"
            msgstr[0] "StringPlural1"
            msgstr[1] "StringsPlural2"
            """,
            "Found unexpected msgstr[*] on the non pluralized entry with msgid 'p1'",
        )

    def test_empty_msgid(self):
        self._test_parse_error(
            """
            msgid ""
            msgstr ""

            msgid ""
            msgstr "Not a plural"
            """,
            "Found empty msgid.",
        )

    def test_duplicate_keys(self):
        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgstr "1"

                msgid "p1"
                msgstr "2"
            """,
            "A duplicate msgid was detected (p1). Use a unique "
            "msgid or add a msgctxt to differentiate",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgctxt "t1"
                msgid "p1"
                msgstr "1"

                msgctxt "t1"
                msgid "p1"
                msgstr "2"
            """,
            "A duplicate msgid was detected (p1). Use a unique msgid or a unique "
            "msgctxt to differentiate (the existing msgctxt 't1' is a duplicate one)",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "1"
                msgstr[1] "2"

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "3"
                msgstr[1] "4"
            """,
            "A duplicate (msgid, msgid_plural) combination was "
            "detected (p1, p2). Use a unique msgid, msgid_plural "
            "combination or add a msgctxt to differentiate",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgctxt "t1"
                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "1"
                msgstr[1] "2"

                msgctxt "t1"
                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "3"
                msgstr[1] "4"
            """,
            "A duplicate (msgid, msgid_plural) combination was "
            "detected (p1, p2). Use a unique msgid, msgid_plural "
            "combination or a unique msgctxt to differentiate "
            "(the existing msgctxt 't1' is a duplicate one)",
        )

    def test_incomplete_plurals(self):
        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "Not a plural"
                msgstr[1] ""
            """,
            "Incomplete plural forms found on the entry with msgid 'p1' and "
            "msgid_plural 'p2'",
        )

    def test_invalid_po_raised_as_parseerror(self):
        source = "blyargh"
        with self.assertRaises(ParseError):
            self.handler.parse(source)

    def test_pot(self):
        sources = [
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr ""

                msgid "two"
                msgstr ""
                """
            ),
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "\\n"

                msgid "two"
                msgstr ""
                """
            ),
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr ""

                msgid "two"
                msgstr "\\n"
                """
            ),
        ]
        templates = []
        for source in sources:
            template, stringset = self.handler.parse(source, is_source=True)
            templates.append(template)
            self.assertEqual(len(stringset), 2)
            self.assertEqual(stringset[0].string, "one")
            self.assertEqual(stringset[1].string, "two")
        for t in templates[1:]:
            self.assertEqual(t, templates[0])

        source = strip_leading_spaces(
            """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgid_plural "ones"
                msgstr[0] ""
                msgstr[1] ""

                msgid "two"
                msgstr ""
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].strings, {0: "one", 1: "ones"})
        self.assertEqual(stringset[1].string, "two")

    def test_spaces_treated_like_not_empty(self):
        source = strip_leading_spaces(
            """
            msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "one"

                msgid "two"
                msgstr "\\n"
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].string, "one")
        self.assertEqual(stringset[1].string, "\n")

        source = strip_leading_spaces(
            """
            msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "\\n"

                msgid "two"
                msgstr "two"
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].string, "\n")
        self.assertEqual(stringset[1].string, "two")


    def test_sync_template_adds_new_non_plural_entry(self):
        """
        When the template has no entries, sync_template should add all
        OpenStrings, and compile should then fill in msgstr correctly.
        """
        string1 = self._create_openstring(False)

        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            """
        )
        template, _ = self.handler.parse(source)

        # Add string1 to an otherwise empty template
        template = self.handler.sync_template(template, [string1])
        compiled = self.handler.compile(template, [string1])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"
                """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_sync_template_adds_new_plural_entry(self):
        """
        sync_template should add plural OpenStrings and compile should expand
        msgstr_plural[0] placeholder into full plural forms.
        """
        string1 = self._create_openstring(True)
        s1_key_singular, s1_key_plural = string1.key.split(":")

        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            """
        )
        template, _ = self.handler.parse(source)

        template = self.handler.sync_template(template, [string1])
        compiled = self.handler.compile(template, [string1])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgid_plural "{s1_key_plural}"
                msgstr[0] "{s1_str_singular}"
                msgstr[1] "{s1_str_plural}"
                """.format(
                    **{
                        "s1_key": s1_key_singular,
                        "s1_key_plural": s1_key_plural,
                        "s1_str_singular": string1.string[0],
                        "s1_str_plural": string1.string[1],
                    }
                )
            ),
        )

    def test_sync_template_adds_and_removes_mixed_entries(self):
        """
        sync_template should remove obsolete entries and add missing ones
        in a single pass, preserving the order of the stringset.
        """
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False)
        string3 = self._create_openstring(False)

        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            msgid "{s2_key}"
            msgstr "{s2_str}"
            """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                }
            )
        )
        template, _ = self.handler.parse(source)

        # We want to keep string2 and add string3, removing string1
        template = self.handler.sync_template(template, [string2, string3])
        compiled = self.handler.compile(template, [string2, string3])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s2_key}"
                msgstr "{s2_str}"

                msgid "{s3_key}"
                msgstr "{s3_str}"
                """.format(
                    **{
                        "s2_key": string2.key,
                        "s2_str": string2.string,
                        "s3_key": string3.key,
                        "s3_str": string3.string,
                    }
                )
            ),
        )


    def test_split_key_roundtrip_with_escaping(self):
        """
        Keys containing ':' and '\\' must be correctly escaped in parse()
        and unescaped by _split_key_to_msgids().
        """
        raw_msgid = 'foo:bar\\baz'
        raw_msgid_plural = 'p:q\\z'  # avoid PO escape like \r

        source = strip_leading_spaces(
            r'''
            msgid ""
            msgstr ""
            "Content-Type: text/plain; charset=UTF-8\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\n"

            msgid "%s"
            msgid_plural "%s"
            msgstr[0] ""
            msgstr[1] ""
            ''' % (raw_msgid, raw_msgid_plural)
        )
        template, stringset = self.handler.parse(source, is_source=True)

        # We expect a single plural OpenString
        self.assertEqual(len(stringset), 1)
        os = stringset[0]

        # 1) Check that our key-splitting logic is the inverse of the escaping in parse()
        msgid, msgid_plural = self.handler._split_key_to_msgids(os.key)
        self.assertEqual(msgid, raw_msgid)
        self.assertEqual(msgid_plural, raw_msgid_plural)

        # 2) Check that sync_template + compile produce a PO file which,
        #    when parsed again, gives us the same raw msgid/msgid_plural
        template2, _ = self.handler.parse(
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                """
            )
        )
        template2 = self.handler.sync_template(template2, [os])
        compiled = self.handler.compile(template2, [os])

        po_reparsed = polib.pofile(compiled)
        # skip header entry (msgid == "")
        entries = [e for e in po_reparsed if e.msgid]
        self.assertEqual(len(entries), 1)
        entry = entries[0]

        self.assertEqual(entry.msgid, raw_msgid)
        self.assertEqual(entry.msgid_plural, raw_msgid_plural)

    def test_make_added_entry_copies_metadata_and_flags(self):
        """
        _make_added_entry should correctly copy flags, occurrences and
        developer comments from OpenString into the new POEntry.
        """
        key = generate_random_string()
        os = OpenString(
            key,
            generate_random_string(),
            order=0,
            pluralized=False,
            context="",
            flags="f1, f2",
            occurrences="file1.py:10, file2.py:20",
            developer_comment="a comment",
        )
        os.string_hash

        entry = self.handler._make_added_entry(os)

        self.assertEqual(entry.msgid, key)
        self.assertEqual(entry.msgstr, os.template_replacement)

        self.assertEqual(sorted(entry.flags), ["f1", "f2"])

        self.assertEqual(
            sorted(entry.occurrences),
            [("file1.py", "10"), ("file2.py", "20")],
        )

        self.assertEqual(entry.comment, "a comment")

        os2 = OpenString(
            key,
            generate_random_string(),
            order=1,
            pluralized=False,
            context="",
            flags=["a", "b"],
            occurrences=[("x.py", "1"), ("y.py", "2")],
            developer_comment=None,
        )
        os2.string_hash

        entry2 = self.handler._make_added_entry(os2)
        self.assertEqual(sorted(entry2.flags), ["a", "b"])
        self.assertEqual(sorted(entry2.occurrences), [("x.py", "1"), ("y.py", "2")])
        self.assertEqual(entry2.comment, "")

    def test_sync_template_plural_add_and_remove_combined(self):
        """
        Combined test for plural sync:
        - remove obsolete plural entry
        - keep existing matching plural entry
        - add a new plural entry
        """
        s_keep = self._create_openstring(True)
        s_obsolete = self._create_openstring(True)
        s_new = self._create_openstring(True)

        k_keep = s_keep.key.split(":")
        k_obsolete = s_obsolete.key.split(":")
        k_new = s_new.key.split(":")

        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{k_keep_s}"
            msgid_plural "{k_keep_p}"
            msgstr[0] "{keep_singular}"
            msgstr[1] "{keep_plural}"

            msgid "{k_obsolete_s}"
            msgid_plural "{k_obsolete_p}"
            msgstr[0] "{obsolete_singular}"
            msgstr[1] "{obsolete_plural}"
            """.format(
                **{
                    "k_keep_s": k_keep[0],
                    "k_keep_p": k_keep[1],
                    "keep_singular": s_keep.string[0],
                    "keep_plural": s_keep.string[1],
                    "k_obsolete_s": k_obsolete[0],
                    "k_obsolete_p": k_obsolete[1],
                    "obsolete_singular": s_obsolete.string[0],
                    "obsolete_plural": s_obsolete.string[1],
                }
            )
        )
        template, _ = self.handler.parse(source)

        template = self.handler.sync_template(template, [s_keep, s_new])
        compiled = self.handler.compile(template, [s_keep, s_new])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{k_keep_s}"
                msgid_plural "{k_keep_p}"
                msgstr[0] "{keep_singular}"
                msgstr[1] "{keep_plural}"

                msgid "{k_new_s}"
                msgid_plural "{k_new_p}"
                msgstr[0] "{new_singular}"
                msgstr[1] "{new_plural}"
                """.format(
                    **{
                        "k_keep_s": k_keep[0],
                        "k_keep_p": k_keep[1],
                        "keep_singular": s_keep.string[0],
                        "keep_plural": s_keep.string[1],
                        "k_new_s": k_new[0],
                        "k_new_p": k_new[1],
                        "new_singular": s_new.string[0],
                        "new_plural": s_new.string[1],
                    }
                )
            ),
        )

    def test_sync_template_adds_entry_with_context(self):
        """
        sync_template should correctly add entries with msgctxt (context).
        """
        key = generate_random_string()
        context = "menu_item"
        string_value = generate_random_string()

        os = OpenString(
            key,
            string_value,
            order=0,
            pluralized=False,
            context=context,
        )
        os.string_hash

        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            """
        )
        template, _ = self.handler.parse(source)

        template = self.handler.sync_template(template, [os])
        compiled = self.handler.compile(template, [os])

        # Verify the compiled output contains msgctxt
        self.assertIn('msgctxt "menu_item"', compiled)
        self.assertIn(f'msgid "{key}"', compiled)
        self.assertIn(f'msgstr "{string_value}"', compiled)

    def test_sync_template_adds_plural_entry_with_context(self):
        """
        sync_template should correctly add pluralized entries with msgctxt.
        """
        msgid = generate_random_string()
        msgid_plural = generate_random_string()
        key = f"{msgid}:{msgid_plural}"
        context = "notification"
        singular = generate_random_string()
        plural = generate_random_string()

        os = OpenString(
            key,
            {0: singular, 1: plural},
            order=0,
            pluralized=True,
            context=context,
        )
        os.string_hash

        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            """
        )
        template, _ = self.handler.parse(source)

        template = self.handler.sync_template(template, [os])
        compiled = self.handler.compile(template, [os])

        # Verify the compiled output contains msgctxt and plural forms
        self.assertIn('msgctxt "notification"', compiled)
        self.assertIn(f'msgid "{msgid}"', compiled)
        self.assertIn(f'msgid_plural "{msgid_plural}"', compiled)
        self.assertIn(f'msgstr[0] "{singular}"', compiled)
        self.assertIn(f'msgstr[1] "{plural}"', compiled)
