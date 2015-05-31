.. _testing:


Testing
#######


1. Get yourself a sample file
=============================

Its a very good idea to start developing by getting a sample source file for
two reasons:

1. It will get picked up by the :ref:`testbed` so you will be able to get
   instant feedback as you work on your handler.

2. You will get a lot of tests for free. These tests will parse the sample file
   into a template and stringset, compile them back in your source file and
   check whether the template matches the expected one and that the resulted
   file matches the source. It will also try to translate the strings based on
   some common ones found in a dictionary and check that it can compile a
   language file that matches the expected one.

Put your sample file in
``openformats/tests/formats/<format_name>/files/1_en.<format_extension>``. For
example, our sample SRT file goes to
``OpenFormats/tests/formats/srt/files/1_en.srt``.


2. Generate expected template and language files
================================================

In order to generate the expected template and language files mentioned above,
you can use the `bin/create_files.py` script once you have a working handler::

    ./bin/create_files.py openformats/tests/formats/srt/files/1_en.srt

In order to get the tests we mentioned for free, make sure your test class
inherits from the:

.. py:module:: openformats.tests.formats.common

.. autoclass:: CommonFormatTestMixin()

You might have noticed that by using a working handler to make the expected
sample files and then testing against them seems pointless. Well, you're right,
they are, initially. The point of for them to serve as regression tests, as you
later make changes to your handler.


3. Add your own tests
=====================

Testing that a handler works correctly against a valid source file is good, but
you will want to also test more things, like:

* The hashes produced take the correct information into account
* The metadata of the extracted strings is what you want
* `ParseErrors` are raised when they should and their message is helpful to
  Transifex users
* Sections of the compiled files are removed when the relevant strings are
  missing from the stringset given as input
* Anything to get your coverage higher


4. Utilities
============

.. py:module:: openformats.tests.utils

.. autofunction:: generate_random_string
.. autofunction:: strip_leading_spaces

.. automethod:: openformats.tests.formats.common.CommonFormatTestMixin._test_parse_error


5. Run the test suite
=====================
::

    python setup.py test
