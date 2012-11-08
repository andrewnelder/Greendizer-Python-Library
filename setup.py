# -*- coding: utf-8 -*-
import sys
import logging


version = float('.'.join(map(str, sys.version_info[0:2])))
if version < 2.5:
    logging.warn('This library has only been tested with Python 2.5+.')


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


install_requires = ['pyxmli >= 2.0.0',]
if version < 2.6:
    install_requires.append('simplejson >= 2.6')


setup(
    name                = 'greendizer',
    packages            = [
                            'greendizer',
                            'greendizer.clients',
                            'greendizer.clients.resources',
                            'greendizer.oauth',
                          ],
    version             = open('VERSION').read(),
    author              = u'Greendizer',
    author_email        = 'support@greendizer.com',
    package_data        = {'greendizer' : ['../VERSION']},
    install_requires    = install_requires,
    url                 = 'https://github.com/Greendizer/Greendizer-Python-Library',
    license             = open('LICENCE').read(),
    description         = 'A Python wrapper of the Greendizer invoicing API.',
)
