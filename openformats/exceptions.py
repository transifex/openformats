class OpenformatsError(Exception):
    pass


class ParseError(OpenformatsError):
    pass


class RuleError(OpenformatsError):
    pass


class MissingParentError(OpenformatsError):
    pass
