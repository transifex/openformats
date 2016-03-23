from hashlib import md5


class OpenString(object):
    """
    This class will abstract away the business of generating hashes out of your
    strings and will serve as a place to get translations from when compiling.
    Several OpenStrings in our process define a *Stringset*, which is simply a
    python list of OpenStrings. To create an OpenString, you need 2 arguments:

    * The 'key'

      Something in your source file that uniquely identifies the section that
      the source string originated from. It might be helpful for your
      compiler to use something that appears in the same form in language
      files as well.

    * The 'string' or 'plural forms of the string':

      If the file format you're working with does not support plural forms,
      or if the string in question is not pluralized, you can just supply the
      string itself as the second argument. If you string is pluralized
      however, you have to supply all plural forms in a dictionary with the
      rule numbers as keys. For example::

          OpenString("UNREAD MESSAGES",
                     {1: "You have %s unread message",
                      5: "You have %s unread messages"})

    * There are a number of optional keyword arguments to `OpenString`:

      context, order, character_limit, occurrences, developer_comment, flags,
      fuzzy, obsolete

    Their main purpose is to provide context to the translators so that they
    can achieve higher quality. Two of them however, though optional, are
    highly recommended:

    * Context

      This is also taken into account when producing the hash, so if you
      can't ensure that your keys aren't unique within the source file, you
      can still get away with ensuring that the `(key, context)` pair is.

    * Order

      If you provide an order (integer), Transifex will save it in the
      database and then, when you try to compile a template against a
      stringset fetched from Transifex, it will already be ordered, even if
      it contains translations. This can allow you to optimize the
      compilation process as the order that the hashes appear in the template
      will be the same as the order of strings in the stringset.

      Another valuable outcome is that the order will be preserved when the
      strings are shown to translators which can provide context and thus
      improve translation quality.

    Once you have created an OpenString, you can get it's hash using the
    `template_replacement` property
    """

    DEFAULTS = {
        'context': "",
        'order': None,
        'character_limit': None,
        'occurrences': None,
        'developer_comment': "",
        'flags': "",
        'fuzzy': False,
        'obsolete': False,
    }

    def __init__(self, key, string_or_strings, **kwargs):
        self.key = key
        if isinstance(string_or_strings, dict):
            self.pluralized = len(string_or_strings) > 1
            self._strings = {key: value
                             for key, value in string_or_strings.items()}
        else:
            self.pluralized = False
            self._strings = {5: string_or_strings}

        for key, value in self.DEFAULTS.items():
            setattr(self, key, kwargs.get(key, value))

        if 'pluralized' in kwargs:
            self.pluralized = kwargs['pluralized']

        self._string_hash = None

    def __hash__(self):
        return hash((self.key, self.context, self.rule))

    def __repr__(self):
        return '"{}"'.format(self._strings[5].encode('utf-8'))  # pragma: nocover # noqa

    @property
    def string(self):
        if self.pluralized:
            return self._strings
        else:
            return self._strings[5]

    def _get_string_hash(self):
        keys = [self.key, self.context or '']
        return md5(':'.join(keys).encode('utf-8')).hexdigest()

    @property
    def string_hash(self):
        if self._string_hash is None:
            self._string_hash = self._get_string_hash()
        return self._string_hash

    @property
    def template_replacement(self):
        suffix = 'pl' if self.pluralized else 'tr'
        return "{hash}_{suffix}".format(hash=self.string_hash, suffix=suffix)
