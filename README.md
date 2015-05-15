

OpenFormats
===========

OpenFormats is a Python library used to localize various file formats. Its
primary use is to work as a backend to [Transifex][tx].

This repository has two components:

1. A library that is to be imported by Transifex and used to handle the various
   file formats.

2. A small webserver used to test the library and to help develop or tweak
   the codebase.

OpenFormats is not intended to convert from one format to the other.


Documentation
-------------

[OpenFormats docs](http://openformats.readthedocs.org/en/latest/) on
ReadTheDocs.


Contribute
----------

To contribute to the library, fork away and submit a pull request.

You can run tests for the formats by doing the following::

    nosetests openformats


The testbed
-----------

To run the testbed:

    ./manage.py syncdb --noinput  # optional
    ./manage.py runserver

Then point your browser to http://localhost:8000/.

The `syncdb` step is optional and is used if you wish to save certain tests by
their URL The tests are saved to an sqlite database. This is most likely to be
useful in the live version of the testbed.

Having fired up the testbed, you can select a format handler, paste some text
and try to parse it. The testbed will show you the stringset that was extracted
from the source text and the template in kept from it. Then, you can try
compiling the template against the stringset, or you can modify it first.



Status
------

[![CircleCI](https://circleci.com/gh/transifex/openformats.svg?style=shield)](https://circleci.com/gh/transifex/openformats)

[![Coveralls](https://coveralls.io/repos/transifex/openformats/badge.svg)](https://coveralls.io/r/transifex/openformats)

[![Documentation Status](https://readthedocs.org/projects/openformats/badge/?version=latest)](https://readthedocs.org/projects/openformats/?badge=latest)


[tx]: http://www.transifex.com/  "Transifex, the Localization Automation Platform"
