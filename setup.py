# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

import versioneer

install_requires = [
    'polib==1.0.3',
    'mistune==0.7.3',
    'PyYAML==5.1',
    'pyparsing==2.2.0',
    'lxml==4.6.2',
    'beautifulsoup4==4.9.0',
    'ucflib @ git+https://github.com/kbairak/ucflib.git@py3_compatibility#egg=ucflib-0.2.1',  # noqa
]

tests_require = [
    'nose',
    'mock',
    'coverage',
    'nosexcover'
]

setup(
    name="openformats",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
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
