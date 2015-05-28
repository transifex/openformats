.. _testing:


Testing
#######


1. Copy the sample tests
========================

* A dummy set of tests can be found at ``openformats/tests/sample/``. Copy the
  directory and customize your handler::

      $ mkdir tests/myformat
      $ cp tests/sample/test_sample.py tests/myformat/test_myformat.py
      [Edit test_myformat.py...]

* Provide a test file for your format: as ``tests/myformat/files/1_en.ext``.


2. Test your handler
====================

Test your handler by trying to compile the template and translation files::

      ./bin/create_files.py openformats/tests/myformat/files/1_en.ext

This will create ``1_tpl.ext`` and ``1_el.ext`` for you to review and use in
the following steps in the tests.


3. Run the test suite
=====================
::

    nosetests -v openformats

