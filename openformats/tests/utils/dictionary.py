# -*- coding: utf-8 -*-

"""
Various methods useful for tests and similar operations.
"""

from __future__ import unicode_literals

import csv
import os
from io import open

import six

root = os.path.dirname(__file__)
DICT_FNAME = os.path.join(root, 'dictionary.csv')

try:
    # This is ugly, but io.open does not work well with csv
    import sys
    six.moves.reload_module(sys)
    sys.setdefaultencoding('utf-8')
except Exception:
    pass


class FunkyDictionary(object):
    def __init__(self):
        self.phrase_list = []
        self.phrase_dict = {}
        with open(DICT_FNAME, 'r', encoding='utf-8', newline=None) as dict_file:
            dict_reader = csv.DictReader(dict_file)
            for phrase in dict_reader:
                unicode_phrase = {}
                for key, value in six.iteritems(phrase):
                    if isinstance(value, six.binary_type):
                        value = value.decode("utf-8")
                    unicode_phrase[key] = value
                self.phrase_list.append(unicode_phrase)
                # We can assume 'en' is going to be used as a source language
                # often, so it makes sense to be able to do quick lookups
                self.phrase_dict[unicode_phrase['en']] = unicode_phrase

    def translate(self, phrase, to_lang, from_lang="en", debug=False):
        if from_lang == "en":
            try:
                if debug:
                    print('Lookup for "{}" successful'.format(phrase[:20]))
                return self.phrase_dict[phrase][to_lang]
            except KeyError:
                pass
        else:
            for dict_phrase in self.phrase_list:
                if phrase == dict_phrase[from_lang]:
                    return dict_phrase[to_lang]
        # Phrase not found in funky dict
        if debug:
            print('Lookup for "{}" unsuccessful.'.format(phrase[:20]))
        return "{}:{}".format(to_lang, phrase)


funky_dictionary = FunkyDictionary()


def translate_stringset(stringset, from_lang="en", to_lang="el", debug=False):
    for s in stringset:
        for rule, pluralform in list(six.iteritems(s._strings)):
            s._strings[rule] = funky_dictionary.translate(
                pluralform, to_lang, from_lang, debug
            )
    return stringset
