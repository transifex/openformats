# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

import versioneer

install_requires = [
    "polib==1.0.3",
    "mistune==0.8.1",
    "PyYAML==6.0.2",
    "pyparsing==3.0.9",
    "lxml==5.0.0",
    "beautifulsoup4==4.9.3",
    "six",
    "ucflib @ git+https://github.com/kbairak/ucflib.git@py3_compatibility#egg=ucflib-0.2.1",  # noqa
]

tests_require = ["pytest", "pytest-cov", "coverage"]

setup(
    name="openformats",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="The Transifex Open Formats library",
    author="Transifex",
    author_email="support@transifex.com",
    url="https://github.com/transifex/openformats",
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="openformats.tests.run_tests.run_all",
    packages=find_packages(where=".", exclude=("tests*", "testbed")),
)
