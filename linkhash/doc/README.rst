========
linkhash
========

`linkhash` is a program that can assist in speeding up your build-system
by skipping unecessary link steps.

-----------------
Problem Statement
-----------------

A common practice in build system design is to declare as a dependency of a
link-step all of the shared objects that go into the link operation. Build
systems will rebuild the output whenever the inputs are newer so that when a
shared object is rebuilt, all of it's transitively dependant objects will
become out of date.

This is somewhat counter to the whole point of shared objects with versioned
interfaces. Indeed it is idomatic to replace a shared object with a newer one
on a live system without relinking every program that uses it.

--------
Solution
--------

In reality, an output (either a binary or another shared library) only needs
to be re-linked if the **API** of a shared object it depends on is changed.
More specifically, the API of a shared shared is the set of all globally
visible symbols it contains.

`linkhash` is a program which inspects a shared object, builds a list of
all externally visible symbols, and hashes that set in a deterministic way.
This API digest serves as a version indicator. Even if the modification time
of a shared object suggests that it is newer than a dependant link output,
if the API digest has not changed since that output was created then it is
not in fact out of date with respect to this input.

This package also includes a program `linkcache` which acts as a command
wrapper (similar to ccache, distcc, icecream, etc) for the linker. It will
intercept the link command and, if the link output is up-to-date with respect
to the inputs (using the above definition) then it will touch the existing
output and forgo the actual link command. Otherwise it will dispatch the
link command.

------------
Installation
------------

For users of ubuntu, you can install `linkhash` from
`ppa:josh-bialkowski/tangent`:

.. code::

  ~# add-apt-repository ppa:josh-bialkowski/tangent
  ~# apt install linkhash

Other linuxes can install from source by building with a cmake generated
build system. There are lots of ways this can be done, but an example is:

.. code::

  ~$ cmake .
  ~$ make
  ~$ sudo make install

-----
Usage
-----

`linkhash`:
===========

.. code::

  ========
  linkhash
  ========
  version: 0.1.0-dev0
  author : Josh Bialkowski <josh.bialkowsk@gmail.com>

  linkhash [-h/--help] [-o/--outfile] [--dump-api] <FILEPATH>


  linkhash computes a sha1sum of the "API" of a shared object (i.e. the list
  of externally visable symbols).


  Flags:
  ------
  -h  --help          print this help message
  -o  --outfile       Path to the file to write. '-' means write to stdout
                      (default)
      --dump-api      If specified, then write out the API specification rather
                      than it's hash

  Positionals:
  ------------
  filepath


`linkcache`:
============

.. code::

  usage: linkcache [-h] [--log-level {debug,info,warning,error}] ...

  Wrap a link command. If the link command can be skipped due to the fact that
  the output is up-to-date with respect to the inputs, then the command is
  skipped and the output is touched instead.

  positional arguments:
    subcommand

  optional arguments:
    -h, --help            show this help message and exit
    --log-level {debug,info,warning,error}


From within cmake
=================

.. code::

  option(ENABLE_LINKCACHE
        "Enable link caching. NOTE: the helper program must also be installed"
        OFF)

  find_package(linkhash QUIET CONFIG)
  if(linkhash_FOUND AND ENABLE_LINKCACHE)
    activate_linkcache(LOG_LEVEL warning)
  endif()

In a makefile
=============

You could simply prefix your linker with `linkcache`, something like

.. code::

  LINK := linkcache $(LD)

Alternatively, you have the opportunity to \"unroll\" this process. When you
write the recipe for your link rule, add a call to `linkhash` to the end
of your recipe, writing out the API digest sidecar file (\*.so.d). Then,
instead of declaring a shared object as a dependency, delcare the sidecar
file (`linkhash` will not write the file if it is unchanged). e.g.

.. code::

  libfoo.so: foo.cc
    g++ -shared -o libfoo.so foo.cc
    linkhash -o libfoo.so.apid libfoo.so

  libfoo.so.apid: libfoo.so

  libbar.so: libfoo.so.apid bar.cc
    g++ -shared -o libbar.so bar.cc
    linkhash -o libbar.so.apid libbar.so

  libbar.so.apid: libbar.so
