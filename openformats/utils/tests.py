
"""
Various methods useful for tests and similar operations.
"""

import csv

DICT_FNAME = "openformats/tests/common/dictionary.csv"

def translate_phrase(phrase, from_lang="en", to_lang="el", debug=False):
    """Lookup a phrase in a dictionary and translate if possible."""
    with open(DICT_FNAME, 'rU') as dict_file:
        dict_reader = csv.DictReader(dict_file)
        for r in dict_reader:
            if r[from_lang] == phrase:
                if debug: print('Lookup for "%s" successful.' % phrase[:20])
                return r[to_lang]
    # Fall back to source lang, differentiate from original string with prefix
    if debug: print('Lookup for "%s" unsuccessful.' % phrase[:20])
    return "%s:%s" % (to_lang, phrase)

def translate_stringset(stringset, from_lang="en", to_lang="el", debug=False):
    for s in stringset:
        for rule, pluralform in s._strings.items():
            s._strings[rule] = translate_phrase(pluralform, from_lang, to_lang,
                                                debug)
    return stringset
