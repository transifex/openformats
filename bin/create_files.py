#!/usr/bin/env python

"""
Create template files from source files using the respective handlers.

Example:
    $ ./bin/create_files.py openformats/tests/srt/files/1_en.srt
"""

from __future__ import absolute_import

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from openformats.formats import plaintext, srt, android, json
from openformats.tests.utils import translate_stringset

args = argparse.ArgumentParser


def get_handler(ext):
    """Return the right format handler based on the file extension."""
    return {
        'txt': plaintext.PlaintextHandler(),
        'srt': srt.SrtHandler(),
        'xml': android.AndroidHandler(),
        'json': json.JsonHandler(),
    }[ext]


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
        if args.debug:
            print("Writing %s" % tpl_fname)
        if args.execute:
            tpl_file.write(template)
        tpl_file.close()

    translated_stringset = translate_stringset(stringset, debug=True)

    # Save translated file
    compiled = handler.compile(template, translated_stringset)
    fname = args.inputfile.replace("_en", "_el")
    with open(fname, 'w+') as f:
        if args.debug:
            print("Writing %s" % fname)
        f.write(compiled)
        f.close()


def main(argv):
    parser = argparse.ArgumentParser(
        add_help=True,
        description='Generate right test files from an English source file.'
    )
    parser.add_argument('inputfile',
                        help="Source file to convert")
    parser.add_argument('-d', '--debug', action='store_true', default=True,
                        help='Print debug information')
    parser.add_argument('-x', '--execute', action='store_true', default=True,
                        help="Actually execute. Otherwise, don't do anything.")
    global args  # Help us access this variable from inside the other methods.
    args = parser.parse_args()
    run()

if __name__ == "__main__":
    main(sys.argv[1:])
