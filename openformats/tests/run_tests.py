import sys
import pytest


def run_all(args=None):
    return pytest.main(
        args
        or [
            "openformats/tests",
            "-v",
            "--cov=openformats",
            "--cov-report=xml",
            "--cov-report=term",
        ]
    )
    # """Run the openformats test suite.

    # All default options (test path, coverage, JUnit XML, log level) are
    # declared in ``pytest.ini`` so this entry point, the ``Makefile``
    # target, and a bare ``pytest`` invocation all behave identically.
    # """
    # return pytest.main(list(args) if args else [])


if __name__ == "__main__":
    sys.exit(run_all(sys.argv[1:]) or 0)
