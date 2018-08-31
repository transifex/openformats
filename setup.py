# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = [
    'polib==1.0.3',
    'mistune==0.7.3',
    'PyYAML==3.10',
    'pyparsing==2.2.0',
    'lxml==4.1.1',
    'UCFlib==0.2.1',
]

tests_require = [
    'nose',
    'mock',
    'coverage',
    'nosexcover'
]

setup(
    name="openformats",
    version='0.0.33',
    description="The Transifex Open Formats library",
    author="Transifex",
    author_email="support@transifex.com",
    url="https://github.com/transifex/openformats",
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="openformats.tests.run_tests.run_all",
    packages=find_packages(
        where='.',
        exclude=('tests*', 'testbed')
    )
)
