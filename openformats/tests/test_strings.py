from hashlib import md5
from random import randint
from unittest import TestCase

from openformats.strings import OpenString

from openformats.tests.utils import generate_random_string


class OpenStringTestCase(TestCase):
    def test_singular_string_is_non_plural(self):
        random_string = generate_random_string()
        open_string = OpenString('test', random_string)

        self.assertEqual(open_string._strings, {5: random_string})
        self.assertFalse(open_string.pluralized)

    def test_singular_dict_is_non_plural(self):
        random_string = {5: generate_random_string()}
        open_string = OpenString('test', random_string)

        self.assertEqual(open_string._strings, random_string)
        self.assertFalse(open_string.pluralized)

    def test_singular_is_returned(self):
        random_string = generate_random_string()
        open_string = OpenString('test', random_string)

        self.assertEqual(open_string.string, random_string)

    def test_plurals_are_returned(self):
        random_strings = {
            i: generate_random_string()
            for i in xrange(randint(10, 20))
            }
        open_string = OpenString('test', random_strings)

        self.assertTrue(open_string.pluralized)
        self.assertEqual(open_string.string, random_strings)

    def test_multiples_are_plural(self):
        test_strings = {
            i: generate_random_string()
            for i in xrange(randint(5, 10))
            }
        open_string = OpenString('test', test_strings)

        self.assertEqual(open_string._strings, test_strings)
        self.assertTrue(open_string.pluralized)

    def test_defaults_are_assigned_to_self(self):
        random_property_name = generate_random_string()
        random_default = generate_random_string()

        backup_defaults = OpenString.DEFAULTS
        OpenString.DEFAULTS = {
            random_property_name: random_default
        }
        open_string = OpenString('test', 'test')
        self.assertEqual(
            getattr(open_string, random_property_name), random_default
        )
        OpenString.DEFAULTS = backup_defaults

    def test_pluralized_is_overridden_with_keyword(self):
        open_string = OpenString('test', 'test', pluralized=True)
        self.assertTrue(open_string.pluralized)

    def test_template_replacement_returns_correct_suffix(self):
        open_string = OpenString('test', 'test')

        # Test when pluralized False
        open_string.pluralized = False
        template_replacement = open_string.template_replacement
        self.assertTrue(template_replacement.endswith('tr'))

        # Test when pluralized True
        open_string.pluralized = True
        template_replacement = open_string.template_replacement
        self.assertTrue(template_replacement.endswith('pl'))

    def test_context_is_hashed_when_present(self):
        random_context = generate_random_string()
        random_key = generate_random_string()
        random_hash = md5(
            ':'.join([random_key, random_context]).encode('utf-8')
        ).hexdigest()

        open_string = OpenString(random_key, 'test')
        open_string.context = random_context

        replacement = open_string.template_replacement
        hash_string = replacement.split('_')[0]

        self.assertEqual(hash_string, random_hash)

    def test_hash_is_calculated_from_components(self):
        random_key = generate_random_string()
        random_context = generate_random_string()
        random_rule = randint(1, 5)
        random_hash = hash((random_key, random_context, random_rule))

        open_string = OpenString(random_key, '')
        open_string.context = random_context
        open_string.rule = random_rule

        self.assertEqual(hash(open_string), random_hash)
