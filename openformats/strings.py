from hashlib import md5


class OpenString(object):
    DEFAULTS = {
        'context': "",
        'order': None,
        'character_limit': None,
        'occurrences': None,
        'developer_comment': "",
        'flags': "",
        'fuzzy': None,
        'obsolete': None,
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

        self._template_replacement = None

    def __hash__(self):
        return hash((self.key, self.context, self.rule))

    def __repr__(self):
        return '"{}"'.format(self._strings[5].encode('utf-8'))  # pragma: nocover

    @property
    def string(self):
        if self.pluralized:
            return self._strings
        else:
            return self._strings[5]

    def _get_template_replacement(self):
        keys = [self.key, self.context or '']
        suffix = 'pl' if self.pluralized else 'tr'

        return "{hash}_{suffix}".format(
            hash=md5(':'.join(keys).encode('utf-8')).hexdigest(),
            suffix=suffix,
        )

    @property
    def template_replacement(self):
        if self._template_replacement is None:
            self._template_replacement = self._get_template_replacement()
        return self._template_replacement
