

OpenFormats
===========

|build-status| |coverage-status| |docs-status|


OpenFormats is a localization file format library, written in Python_.

* Read and write to various file formats such as `.po`, `.xliff` or even ones
  which are not localization formats, such as `.srt` and `.txt`.
* Plural support for the formats which do support it.
* Built-in web-based test app, to help you develop your own format handlers.

OpenFormats' primary use is to work as a file format backend to Transifex_.

Check out `OpenFormats documentation`_ for more information.


How to get help, contribute, or provide feedback
------------------------------------------------

See our `contribution submission and feedback guidelines`_.

You can run tests for the formats by doing the following::

    python setup.py test


Source code
-----------

The source code for OpenFormats is `hosted on GitHub`_.


The testbed
-----------

To run the testbed::

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


.. Links

.. _Python: http://www.python.org/
.. _Transifex: http://www.transifex.com/
.. _`contribution submission and feedback guidelines`: http://openformats.readthedocs.org/en/latest/contributing.html
.. _`OpenFormats documentation`: http://openformats.readthedocs.org/
.. _`hosted on GitHub`: https://github.com/transifex/openformats


.. |build-status| image:: https://img.shields.io/circleci/project/transifex/openformats.svg
   :target: https://circleci.com/gh/transifex/openformats
   :alt: Circle.ci: continuous integration status
.. |coverage-status| image:: https://img.shields.io/coveralls/transifex/openformats.svg
   :target: https://coveralls.io/r/transifex/openformats
   :alt: Coveralls: code coverage status
.. |docs-status| image:: https://readthedocs.org/projects/openformats/badge/?version=latest
	:target: https://readthedocs.org/projects/openformats/?badge=latest
	:alt: Documentation Status
