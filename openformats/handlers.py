from openformats.exceptions import RuleError

class Handler(object):

    _RULES_ATOI = {
        'zero': 0,
        'one': 1,
        'two': 2,
        'few': 3,
        'many': 4,
        'other': 5
    }

    _RULES_ITOA = {value: key for key, value in _RULES_ATOI.iteritems()}

    _RULE_ERROR_MSG = (
        '{attempted} is not a valid rule value. Valid choices are {valid}'
    )

    @classmethod
    def get_rule_number(cls, string_value):
        try:
            return cls._RULES_ATOI[string_value]
        except KeyError:
            msg = cls._RULE_ERROR_MSG.format(
                attempted=string_value, valid=cls._RULES_ATOI.keys()
            )
            raise RuleError(msg)

    @classmethod
    def get_rule_string(cls, number_value):
        try:
            return cls._RULES_ITOA[number_value]
        except KeyError:
            msg = cls._RULE_ERROR_MSG.format(
                attempted=number_value, valid=cls._RULES_ITOA.keys()
            )
            raise RuleError(msg)

    def parse(self, content):
        # Parse input and return template and stringset
        raise NotImplemented('Abstract method')

    def compile(self, template, stringset):
        # uses template and stringset and returns the compiled file
        raise NotImplemented('Abstract method')
