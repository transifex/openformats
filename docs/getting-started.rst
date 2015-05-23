.. _getting-started:


Getting Started Guide
#####################

Here are some quick steps to get you started with OpenFormats.


Installation
============

To use OpenFormats as a Python library, simply install it with ``pip``,
prefixing with ``sudo`` if permissions warrant::

    pip install openformats

If you plan to tweak the codebase or add your own format handler, grab a copy
of the whole repository from GitHub::

    git clone https://github.com/transifex/openformats.git
    cd openformats


Creating your own handler
=========================

OpenFormats supports a variety of file formats, including plaintext (``.txt``),
subtitles (``.srt``) and others. Here are the steps to create your own handler.


1. Copy the sample handler
--------------------------

A dummy :ref:`handler` can be found at ``openformats/formats/sample.py``. You
can copy and adjust to your own liking. The basic functionality of a handler
is as follows.


``Parse`` method:
~~~~~~~~~~~~~~~~~

* Accept a string (``content``) as an argument.
* Responsible for accepting a string (``content``) and outputting:
  * A template, which is the same string but with the English content removed.
  * A stringset, which is a collection of `OpenString`s

Typically this is done in the following way:

* Use a library or own code to segment (deserialize) the content into
  translatable entities.
* Choose a key to uniquely identify the entity.
* Create a ``OpenString`` object representing the entity.
* Create a hash to replace the original content with.
* Create a stringset with the content
* Use library or own code to serialize stringset back into a template.


``Compile`` method:
~~~~~~~~~~~~~~~~~~~

* Accept a template and a stringset as arguments.
* Walk through the template and replace all hashes with the respective
  content from the stringset.


2. Copy the sample tests
------------------------

* A dummy set of tests can be found at ``openformats/tests/sample/``. Copy the
  directory and customize your handler::

      $ mkdir tests/myformat
      $ cp tests/sample/test_sample.py tests/myformat/test_myformat.py
      [Edit test_myformat.py...]

* Provide a test file for your format: as ``tests/myformat/files/1_en.ext``.


3. Test your handler
--------------------

Test your handler by trying to compile the template and translation files::

      ./bin/create_files.py openformats/tests/myformat/files/1_en.ext

This will create ``1_tpl.ext`` and ``1_el.ext`` for you to review and use in
the following steps in the tests.


4. Run the test suite
---------------------
::

    nosetests -v openformats


Continue reading the other documentation sections for more detail.
