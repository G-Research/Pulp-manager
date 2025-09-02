#!/usr/bin/env python
"""setup.py
"""

from setuptools import setup
try:
    import unittest2 as unittest  # for Python <= 2.6
except ImportError:
    import unittest

PKG_NAME = 'hashi_vault_client'


def test_suite_discovery():
    """Finds test suite.
    """
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('unit_tests', pattern='*_test.py')
    return test_suite


setup(
    name=PKG_NAME,
    version='0.2.3',
    description='A python wrapper around hvac for specific needs',
    author='G-Research',
    license='Apache-2.0',
    packages=[PKG_NAME],
    install_requires=['requests', 'hvac'],
    setup_requires=['pytest-runner', 'hvac'],
    tests_require=['pytest', 'hvac'],
    test_suite='setup.test_suite_discovery',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License'
    ],
)
