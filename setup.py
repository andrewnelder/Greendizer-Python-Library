# -*- coding: utf-8 -*-
import sys
import logging


version = float('.'.join(map(str, sys.version_info[0:2])))
if version < 2.5:
    logging.warn('This library has only been tested with Python 2.5+.')


try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup


'''
"simplejson is the externally maintained development version of the json
library included with Python 2.6 and Python 3.0, but maintains backwards 
compatibility with Python 2.5."

(http://pypi.python.org/pypi/simplejson/)
'''
install_requires = ['pyxmli >= 0',]
if version < 2.6:
    install_requires.append('simplejson >= 2.6')
    
    
setup(
    name                = 'greendizer',
    packages            = ['greendizer'],
    version             = open('VERSION').read(),
    author              = u'Greendizer',
    author_email        = 'support@greendizer.com',
    namespace_packages  = ['greendizer'],
    package_data        = {'greendizer' : ['../VERSION']},
    install_requires    = install_requires,
    url                 = 'https://github.com/Greendizer/' /
                            'Greendizer-Python-Library',
    license             = open('LICENCE').read(),
    description         = 'Create XMLi 2.0 invoices in Python.',
    test_suite          = 'tests'
)