import six

from openformats.exceptions import RuleError
from openformats.strings import OpenString


class Handler(object):
    """
    This class defines the interface you need to implement in order to create a
    handler. Both the `parse` and `compile` methods must be implemented.
    """

    name = None
    extension = None

    _RULES_ATOI = {"zero": 0, "one": 1, "two": 2, "few": 3, "many": 4, "other": 5}

    EXTRACTS_RAW = True

    # Use this flag for handlers whose the content should be processed as
    # binary and not be converted to unicode
    PROCESSES_BINARY = False

    _RULES_ITOA = {value: key for key, value in six.iteritems(_RULES_ATOI)}

    _RULE_ERROR_MSG = "{attempted} is not a valid rule value. Valid choices are {valid}"

    @classmethod
    def get_rule_number(cls, string_value):
        try:
            return cls._RULES_ATOI[string_value]
        except KeyError:
            msg = cls._RULE_ERROR_MSG.format(
                attempted=string_value, valid=list(six.iterkeys(cls._RULES_ATOI))
            )
            raise RuleError(msg)

    @classmethod
    def get_rule_string(cls, number_value):
        try:
            return cls._RULES_ITOA[number_value]
        except KeyError:
            msg = cls._RULE_ERROR_MSG.format(
                attempted=number_value, valid=list(six.iterkeys(cls._RULES_ITOA))
            )
            raise RuleError(msg)

    def parse(self, content, is_source=False):
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

        raise NotImplementedError("Abstract method")  # pragma: no cover

    def compile(self, template, stringset, **kwargs):
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

        raise NotImplementedError("Abstract method")  # pragma: no cover

    def sync_template(self, template: str, stringset: list[OpenString]) -> str:
        """
        Syncs the template with the stringset. If not implemented, it will have
        no effect - the initial template will just be returned.

        Otherwise, it is responsible for deleting strings from the template that
        are not in the stringset and adding strings to the template that exist in
        the stringset but not in the template currently.

        Returns the updated template.
        """
        stringset = list(stringset)
        template = self.remove_strings_from_template(template, stringset)
        template = self.add_strings_to_template(template, stringset)
        return template

    def remove_strings_from_template(
        self, template: str, stringset: list[OpenString]
    ) -> str:
        """
        Removes strings from the template that are not in the stringset.
        """
        return template

    def add_strings_to_template(
        self, template: str, stringset: list[OpenString]
    ) -> str:
        """
        Adds strings to the template that are not in the template currently.
        """
        return template
