Envoy
=====

Envoy is an XMPP platform designed for team collaboration.

## Generating documentation

The documentation for Envoy is written using [ZippyDoc](http://cryto.net/zippydoc). To install ZippyDoc and the
zpy2html converter, run `pip install zippydoc` or install the `zippydoc` package otherwise.


## Development environment setup

1. Install ejabberd, MySQL, Python, and a HTTPd with PHP.
2. Install Python modules `SleekXMPP`, `passlib`, `oursql`.
3. Symlink `/usr/lib/python2.*/site-packages/envoyxmpp` to the `src/envoyxmpp` directory in this repository.
