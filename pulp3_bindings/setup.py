#!/usr/bin/env python
"""setup.py
"""

from setuptools import setup
try:
    import unittest2 as unittest  # for Python <= 2.6
except ImportError:
    import unittest

PKG_NAME = 'pulp3_bindings'


setup(
    name=PKG_NAME,
    version='0.0.20',
    description='A python wrapper around hvac for specific needs',
    author='G-Research',
    license='Apache-2.0',
    packages=['pulp3', 'pulp3.resources'],
    install_requires=['requests', 'pydantic==1.9.2'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License'
    ],
)
