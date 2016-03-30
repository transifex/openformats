from openformats.exceptions import RuleError


class Handler(object):
    """
    This class defines the interface you need to implement in order to create a
    handler. Both the `parse` and `compile` methods must be implemented.
    """

    name = None
    extension = None

    _RULES_ATOI = {
        'zero': 0,
        'one': 1,
        'two': 2,
        'few': 3,
        'many': 4,
        'other': 5
    }

    EXTRACTS_RAW = True

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
        """
        Parses the content, extracts translatable strings into a stringset,
        replaces them with hashes and returns a tuple of the template with the
        stringset

        Typically this is done in the following way:

        * Use a library or your own code to segment (deserialize) the content
          into translatable entities.
        * Choose a key to uniquely identify the entity.
        * Create an ``OpenString`` object representing the entity.
        * Create a hash to replace the original content with.
        * Create a stringset with the content.
        * Use library or own code to serialize stringset back into a template.
        """

        raise NotImplemented('Abstract method')  # pragma: no cover

    def compile(self, template, stringset):
        """
        Parses the template, finds the hashes, replaces them with strings from
        the stringset and returns the compiled file. If a hash in the template
        isn't found in the stringset, it's a good practice to remove the whole
        string section surrounding it

        Typically this is done in the following way:

        * Use a library or own code to segment (deserialize) the template into
          translatable entities, as if assuming that the hashes are the
          translatable entities.
        * Make sure the hash matches the first string in the stringset.
        * Replace the hash with the string.
        * Use library or own code to serialize stringset back into a compiled
          file.

        You can safely assume that the stringset will have strings in the
        correct order for the above process and thus you will probably be able
        to perform the whole compilation in a single pass.
        """

        raise NotImplemented('Abstract method')  # pragma: no cover
