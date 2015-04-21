# txformats

Opensource transifex-independent library for creating/editing/testing file
formats for transifex.com

This repository consists of two features:

1. A library that is to be imported by Transifex and used to handle the various
   file formats.

2. A small webserver that tests this library against data in real-time.


## The testbed

It's very easy to get started with the testbed, simply:

```bash
git clone https://github.com/transifex/txformats
cd txformats
./manage.py syncdb --noinput  # optional
./manage.py runserver
```

then point your browser to http://localhost:8000/.

The `syncdb` step is optional and is used if you wish to save certain tests by
their URL The tests are saved to an sqlite database. This is most likely to be
useful in the live version of the testbed.

Having fired up the testbed, you can select a format handler, paste some text
and try to parse it. The testbed will show you the stringset that was extracted
from the source text and the template in kept from it. Then, you can try
compiling the template against the stringset, or you can modify it first.

## The library

TODO: ...
