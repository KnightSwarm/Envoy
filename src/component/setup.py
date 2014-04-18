#!/usr/bin/env python

"""
distutils/setuptools install script. See inline comments for packaging documentation.
"""

import os
import sys

try:
  from setuptools import setup, find_packages
  # hush pyflakes
  setup
except ImportError:
  from distutils.core import setup

try:
  from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
  from distutils.command.build_py import build_py

packages = find_packages()
#packages = ['envoyxmpp', "envoyxmpp.core"]

#package_dir = {"envoyxmpp": "envoyxmpp", "envoyxmpp.core": "envoyxmpp/core"}

package_data = {}

scripts = []

requires = []

with open("requirements.txt", "r") as f:
  requires += [line.strip() for line in f.read().splitlines()]

with open("optional_deps.txt", "r") as f:
  requires += [line.strip() for line in f.read().splitlines()]

setup(
  name='envoyxmpp',
  version='0.1',
  maintainer='Sven Slootweg',
  maintainer_email='sven.slootweg@knightswarm.com',
  description='XMPP component library for the Envoy persistent chat application.',
  packages=packages,
  #package_dir=package_dir,
  package_data=package_data,
  include_package_data=True,
  scripts=scripts,
  install_requires=requires,
  cmdclass={'build_py': build_py}
)

