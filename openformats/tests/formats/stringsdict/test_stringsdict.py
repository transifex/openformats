import unittest

from openformats.strings import OpenString

from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import (
    generate_random_string, strip_leading_spaces
)

from openformats.formats.stringsdict import StringsDictHandler


class StringsDictTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = StringsDictHandler
    TESTFILE_BASE = "openformats/tests/formats/stringsdict/files"

    def setUp(self):
        super(StringsDictTestCase, self).setUp()
        self.handler = StringsDictHandler()

    def _create_pluralized_string(self):
        context_dict = {
            'main_key': generate_random_string(),
            'secondary_key': generate_random_string(),
            'singular': generate_random_string(),
            'plural': generate_random_string()
        }
        openstring = OpenString(
            context_dict['main_key'],
            {
                1: context_dict['singular'],
                5: context_dict['plural']
            },
            order=0,
            context=context_dict['secondary_key'],
            pluralized=True
        )
        context_dict['hash'] = openstring.template_replacement
        return context_dict, openstring

    def test_string(self):
        context_dict, openstring = self._create_pluralized_string()
        source = strip_leading_spaces(u"""
            <plist>
            <dict>
                <key>{main_key}</key>
                <dict>
                    <key>NSStringLocalizedFormatKey</key>
                    <string>%1$#@a_var@</string>
                    <key>{secondary_key}</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string>{singular}</string>
                        <key>other</key>
                        <string>{plural}</string>
                    </dict>
                </dict>
            </dict>
            </plist>
        """.format(**context_dict))
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])
        self.assertEquals(
            template,
            strip_leading_spaces(u'''
                <plist>
                <dict>
                    <key>{main_key}</key>
                    <dict>
                        <key>NSStringLocalizedFormatKey</key>
                        <string>%1$#@a_var@</string>
                        <key>{secondary_key}</key>
                        <dict>
                            <key>NSStringFormatSpecTypeKey</key>
                            <string>NSStringPluralRuleType</string>
                            <key>NSStringFormatValueTypeKey</key>
                            <string>d</string>
                            <tx_awesome_key_tag></tx_awesome_key_tag>
                            <tx_awesome_string_tag>{hash}</tx_awesome_string_tag>
                        </dict>
                    </dict>
                </dict>
                </plist>
            '''.format(**context_dict)
            )
        )
        self.assertEquals(len(stringset), 1)
        self.assertEquals(stringset[0].__dict__, openstring.__dict__)
        self.assertEquals(compiled, source)

    def test_removes_untranslated(self):
        context_dict, openstring = self._create_pluralized_string()
        source = strip_leading_spaces(u"""
            <plist>
            <dict>
                <key>main_key</key>
                <dict>
                    <key>NSStringLocalizedFormatKey</key>
                    <string>%1$#@a_var@</string>
                    <key>secondary_key_1</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string>removed_one_1</string>
                        <key>other</key>
                        <string>removed_other_1</string>
                    </dict>
                    <key>secondary_key_2</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string>removed_one_2</string>
                        <key>other</key>
                        <string>removed_other_2</string>
                    </dict>
                </dict>
                <key>{main_key}</key>
                <dict>
                    <key>NSStringLocalizedFormatKey</key>
                    <string>%1$#@a_var@</string>
                    <key>{secondary_key}</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string>{singular}</string>
                        <key>other</key>
                        <string>{plural}</string>
                    </dict>
                </dict>
            </dict>
            </plist>
        """.format(**context_dict))
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [openstring])
        self.assertEquals(
            compiled,
            strip_leading_spaces(u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>NSStringLocalizedFormatKey</key>
                        <string>%1$#@a_var@</string>
                    </dict>
                    <key>{main_key}</key>
                    <dict>
                        <key>NSStringLocalizedFormatKey</key>
                        <string>%1$#@a_var@</string>
                        <key>{secondary_key}</key>
                        <dict>
                            <key>NSStringFormatSpecTypeKey</key>
                            <string>NSStringPluralRuleType</string>
                            <key>NSStringFormatValueTypeKey</key>
                            <string>d</string>
                            <key>one</key>
                            <string>{singular}</string>
                            <key>other</key>
                            <string>{plural}</string>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """.format(**context_dict))
        )

    def test_ignores_normal_string_placeholders(self):
        source = strip_leading_spaces(u"""
            <plist>
            <dict>
                <key>a_main_key</key>
                <dict>
                    <key>NSStringLocalizedFormatKey</key>
                    <string>%1$#@a_var@</string>
                    <key>a_secondary_key</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string></string>
                        <key>other</key>
                        <string></string>
                    </dict>
                </dict>
            </dict>
            </plist>
        """)
        template, stringset = self.handler.parse(source)
        self.assertEquals(template, source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, source)

    def test_ignores_closed_string_placeholders(self):
        source = strip_leading_spaces(u"""
            <plist>
            <dict>
                <key>a_main_key</key>
                <dict>
                    <key>NSStringLocalizedFormatKey</key>
                    <string>%1$#@a_var@</string>
                    <key>a_secondary_key</key>
                    <dict>
                        <key>NSStringFormatSpecTypeKey</key>
                        <string>NSStringPluralRuleType</string>
                        <key>NSStringFormatValueTypeKey</key>
                        <string>d</string>
                        <key>one</key>
                        <string/>
                        <key>other</key>
                        <string/>
                    </dict>
                </dict>
            </dict>
            </plist>
        """)
        template, stringset = self.handler.parse(source)
        self.assertEquals(template, source)
        compiled = self.handler.compile(template, [])
        self.assertEquals(compiled, source)

    """ Test Error Raises """

    def test_missing_plural_string(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>secondary_key</key>
                        <dict>
                            <key>one</key>
                            <string>singular</string>
                            <key>other</key>
                            <string></string>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """,
            u'Missing string(s) in <string> tag(s) in the <dict> tag on line 7'
        )

    def test_no_value_for_key(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                </dict>
                </plist>
            """,
            u"Did not find a value for the <key> tag on line 4"
        )

    def test_duplicate_main_key(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>secondary_key</key>
                        <dict>
                            <key>one</key>
                            <string>singular</string>
                            <key>other</key>
                            <string>plural</string>
                        </dict>
                    </dict>
                    <key>main_key</key>
                    <dict>
                        <key>other_key</key>
                        <dict>
                            <key>one</key>
                            <string>singular</string>
                            <key>other</key>
                            <string>plural</string>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """,
            u"Duplicate main key (main_key) found on line 14"
        )

    def test_no_dict_when_expected(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>secondary_key</key>
                        <string>
                            <key>one</key>
                            <string>singular</string>
                            <key>other</key>
                            <string>plural</string>
                        </string>
                    </dict>
                </dict>
                </plist>
            """,
            u"Was expecting <dict> tag but found <string> tag on line 7"
        )

    def test_missing_strings(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>secondary_key</key>
                        <dict>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """,
            u"No plurals found in <dict> tag on line 7"
        )

    def test_wrong_plural_raises_error(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <key>main_key</key>
                    <dict>
                        <key>secondary_key</key>
                        <dict>
                            <key>wrong_plural</key>
                            <string>singular</string>
                            <key>other</key>
                            <string>plural</string>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """,
            u"The plural <key> tag on line 8 contains an invalid plural rule: "
            u"`wrong_plural`"
        )

    def test_no_key_tag_in_dict(self):
        self._test_parse_error(
            u"""
                <plist>
                <dict>
                    <no_key>main_key</no_key>
                    <dict>
                        <key>secondary_key</key>
                        <dict>
                            <key>one</key>
                            <string>singular</string>
                            <key>other</key>
                            <string>plural</string>
                        </dict>
                    </dict>
                </dict>
                </plist>
            """,
            u"Was expecting <key> tag but found <no_key> tag on line 4"
        )
