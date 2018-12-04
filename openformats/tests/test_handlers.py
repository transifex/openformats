from unittest import TestCase

from openformats.exceptions import RuleError
from openformats.handlers import Handler


class HandlerTestCase(TestCase):
    def setUp(self):
        self.handler = Handler()

    def tearDown(self):
        self.handler = None

    def test_get_rule_number_returns(self):
        rules = {
            'zero': 0,
            'one': 1,
            'two': 2,
            'few': 3,
            'many': 4,
            'other': 5
        }
        for rule_str, rule in rules.iteritems():
            self.assertEqual(self.handler.get_rule_number(rule_str), rule)

    def test_get_rule_string_returns(self):
        rules = {
            0: 'zero',
            1: 'one',
            2: 'two',
            3: 'few',
            4: 'many',
            5: 'other',
        }
        for rule, rule_str in rules.iteritems():
            self.assertEqual(self.handler.get_rule_string(rule), rule_str)

    def test_get_rule_string_returns_error(self):
        self.assertRaises(RuleError, self.handler.get_rule_string, 50)

    def test_get_rule_number_returns_error(self):
        self.assertRaises(RuleError, self.handler.get_rule_number, 'test')
