from openformats.formats.json_plurals import JsonPluralsHandler
from ..beta_keyvaluejson.test_json import JsonTestCase

from openformats.exceptions import ParseError


class JsonPluralsTestCase(JsonTestCase):

    HANDLER_CLASS = JsonPluralsHandler
    TESTFILE_BASE = "openformats/tests/formats/keyvaluejson_plurals/files"

    def setUp(self):
        super(JsonPluralsTestCase, self).setUp()
        self.handler = JsonPluralsHandler()

    def test_invalid_plural_format(self):
        # Test various cases of messed-up braces
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have file_count} file.} other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file. other {You have {file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, one {You have {file_count} file}. other {You have file_count} files.} }" }',  # noqa
            'Invalid format of pluralized entry with key: "total_files"'
        )

    def test_invalid_plural_rules(self):
        # Only the following strings are allowed as plural rules:
        #   zero, one, few, many, other
        # Anything else, including their TX int equivalents are invalid.
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, 1 {file} 5 {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): 1, 5 in pluralized entry with key: total_files'  # noqa
        )
        self._test_parse_error_message(
            '{ "total_files": "{ item_count, plural, once {file} mother {{file_count} files} }" }',  # noqa
            'Invalid plural rule(s): once, mother in pluralized entry with key: total_files'  # noqa
        )

    def test_intermediate_whitespace_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        expected_translations = {0: 'Empty', 5: '{count} files'}

        self._test_translations_equal(
            '{'
            '    "k": "{ cnt, plural, zero {Empty} other {{count} files} }"'
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{'
            '    "k": "{cnt,plural,zero{Empty}other{{count} files} }"'
            '}',
            expected_translations
        )
        self._test_translations_equal(
            '{ "k": "{    cnt,  plural,     zero  {Empty} other   {{count} files} }   "     }',  # noqa
            expected_translations
        )

    def test_whitespace_in_translations_not_ignored(self):
        # Whitespace between the various parts of the message format structure
        # should be ignored.
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty} other {{count} files} }"}',
            {0: ' Empty', 5: '{count} files'}
        )
        self._test_translations_equal(
            '{"k": "{ cnt, plural, zero { Empty  } other {{count} files } }"}',
            {0: ' Empty  ', 5: '{count} files  '}
        )

    def _test_parse_error_message(self, source, msg_substr):
        error_raised = False
        try:
            self.handler.parse(source)
        except ParseError as e:
            self.assertIn(
                msg_substr,
                e.message
            )
            error_raised = True
        self.assertTrue(error_raised)

    def _test_translations_equal(self, source, translations_by_rule):
        template, stringset = self.handler.parse(source)
        for rule_int in translations_by_rule.keys():
            self.assertEqual(
                translations_by_rule[rule_int],
                stringset[0].string[rule_int]
            )
