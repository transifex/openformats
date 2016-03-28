from os.path import abspath, dirname
import sys

import nose


def run_all(args=None):
    if not args:
        args = [
            'nosetests', '--with-xunit', '--with-xcoverage',
            '--cover-package=openformats', '--cover-erase',
            '--logging-filter=openformats', '--logging-level=DEBUG',
            '--verbose',
        ]

    nose.run_exit(
        argv=args,
        defaultTest=abspath(dirname(__file__))
    )


if __name__ == '__main__':
    run_all(sys.argv)
