#!/usr/bin/env python

"""
Create template files from source files using the respective handlers.

Example:
    $ ./bin/create_files.py openformats/tests/srt/files/1_en.srt
"""

import argparse
import csv
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from openformats.formats import (plaintext, srt)

args = argparse.ArgumentParser
DICT_FNAME = "openformats/tests/common/dictionary.csv"


def get_handler(ext):
    """Return the right format handler based on the file extension."""
    return {
        'txt': plaintext.PlaintextHandler(),
        'srt': srt.SrtHandler(),
    }[ext]

def translate(phrase, from_lang="en", to_lang="el"):
    """Lookup a phrase in a dictionary and translate if possible."""
    with open(DICT_FNAME, 'rU') as dict_file:
        dict_reader = csv.DictReader(dict_file)
        for r in dict_reader:
            if r[from_lang] == phrase:
                if args.debug: print('Found "%s"' % phrase[0:30])
                return r[to_lang]
    # Fall back to source lang, differentiate from original string with prefix
    return "%s:%s" % (to_lang, phrase)


def run():
    # Choose correct handler based on the file extension
    file_extension = os.path.splitext(args.inputfile)[1][1:]
    handler = get_handler(file_extension)

    with open(args.inputfile, mode='rU') as f:
        source_contents = f.read()

    # Save template test file, eg. 1_tpl.foo
    template, stringset = handler.parse(source_contents)
    tpl_fname = args.inputfile.replace("_en", "_tpl")
    with open(tpl_fname, 'w+') as tpl_file:
        if args.debug: print("Writing %s" % tpl_fname)
        if args.execute:
            tpl_file.write(template)
        tpl_file.close()

    # Translate phrase
    for s in stringset:
        for rule, pluralform in s._strings.items():
            s._strings[rule] = translate(pluralform)

    # Save translated file
    compiled = handler.compile(template, stringset)
    fname = args.inputfile.replace("_en", "_el")
    with open(fname, 'w+') as f:
        if args.debug: print("Writing %s" % fname)
        f.write(compiled)
        f.close()
        

def main(argv):
    parser = argparse.ArgumentParser(add_help=True,
        description='Generate right test files from an English source file.')
    parser.add_argument('inputfile',
                        help="Source file to convert")
    parser.add_argument('-d', '--debug', action='store_true', default=True,
                        help='Print debug information')
    parser.add_argument('-x', '--execute', action='store_true', default=True,
                        help="Actually execute. Otherwise, don't do anything.")
    global args # Help us access this variable from inside the other methods.
    args = parser.parse_args()
    run()

if __name__ == "__main__":
   main(sys.argv[1:])
