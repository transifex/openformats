.. _getting-started:


Getting Started Guide
#####################

Here are some quick steps to get you started with OpenFormats.


Installation
============

To use OpenFormats as a Python library, simply install it with ``pip``,
prefixing with ``sudo`` if permissions warrant::

    pip install pelican markdown

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
  * A stringset, which is a collection of `String`s

Typically this is done in the following way:

* Use a library or own code to segment (deserialize) the content into
  translatable entities.
* Choose a key to uniquely identify the entity.
* Create a ``String`` object representing the entity.
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

A dummy set of tests can be found at ``openformats/tests/sample/``. Copy the
directory and uncomment the relevant lines in ``sample_test.py``.

Then, provide a test file for your file format in
``openformats/tests/sample/files/``. You'll need at least the following files
(replace ``sample`` with your own extension:

* ``1_en.sample``
* ``1_tpl.sample``
* ``1_el.sample``

The repository has a handy script to generate the ``tpl`` and ``el`` for you
using the library itself::

    ./bin/create_files.py openformats/tests/sample/files/1_en.sample

This way you can frequently update your English file with new strings and
corner-cases to test.


Continue reading the other documentation sections for more detail.

.. _Tutorials: https://github.com/getpelican/pelican/wiki/Tutorials
