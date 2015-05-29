from random import randint
from unittest import TestCase

from openformats.exceptions import RuleError
from openformats.handlers import Handler

from openformats.tests.utils import generate_random_string


class HandlerTestCase(TestCase):
    def setUp(self):
        self.handler = Handler()

    def tearDown(self):
        self.handler = None

    def test_get_rule_number_returns(self):
        random_string = generate_random_string()
        random_integer = randint(1, 50)

        self.handler.__class__._RULES_ATOI = {
            random_string: random_integer
        }
        self.assertEqual(
            self.handler.get_rule_number(random_string), random_integer
        )

    def test_get_rule_string_returns(self):
        random_string = generate_random_string()
        random_integer = randint(1, 50)

        self.handler.__class__._RULES_ITOA = {
            random_integer: random_string
        }
        self.assertEqual(
            self.handler.get_rule_string(random_integer), random_string
        )

    def test_get_rule_string_returns_error(self):
        self.assertRaises(RuleError, self.handler.get_rule_string, 50)

    def test_get_rule_number_returns_error(self):
        self.assertRaises(RuleError, self.handler.get_rule_number, 'test')
