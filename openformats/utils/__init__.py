from ..exceptions import RuleError

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


def get_rule_number(string_value):
    try:
        return _RULES_ATOI[string_value]
    except KeyError:
        msg = _RULE_ERROR_MSG.format(
            attempted=string_value, valid=_RULES_ATOI.keys()
        )
        raise RuleError(msg)


def get_rule_string(number_value):
    try:
        return _RULES_ITOA[number_value]
    except KeyError:
        msg = _RULE_ERROR_MSG.format(
            attempted=number_value, valid=_RULES_ITOA.keys()
        )
        raise RuleError(msg)
