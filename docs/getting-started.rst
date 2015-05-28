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


1. Subclass the base `Handler`
==============================

.. py:module:: openformats.handlers

.. autoclass:: Handler
   :members:

Following are some classes that will help you with this process:


2. The `OpenString` class
=========================

.. py:module:: openformats.strings

.. autoclass:: OpenString
   :members:


3. The `Transcriber`
====================

.. py:module:: openformats.transcribers

.. autoclass:: Transcriber
    :members:



Continue reading the other documentation sections for more detail.
