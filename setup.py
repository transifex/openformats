# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = [

]

tests_require = [
    'nose',
    'mock',
    'coverage',
    'nosexcover'
]

setup(
    name="openformats",
    version='0.0.1',
    description="The Transifex open formats library",
    author="Transifex",
    author_email="support@transifex.com",
    url="https://github.com/transifex/openformats",
    install_requires=install_requires,
    tests_require=tests_require,
    dependency_links=tests_require,
    test_suite="",
    packages=find_packages(
        where='.',
        exclude=('tests*', 'testbed')
    )
)
