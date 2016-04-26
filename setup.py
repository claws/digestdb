#!/usr/bin/env python3

''' Installation script for digestdb. '''


# Always prefer setuptools over distutils
from setuptools import setup
from os import path


short_description = (
    'digestdb is a database for storing binary data in a '
    'balanced set of file system directories and providing access to '
    'this data via tradiational database style (e.g. SQL) access.')

long_description = short_description

here = path.abspath(path.dirname(__file__))

setup(
    name='digestdb',
    version='0.0.1a1',
    description=short_description,
    long_description=long_description,
    url='https://github.com/claws/digestdb',
    author='Chris Laws',
    author_email='clawsicus@gmail.com',
    license='MPL 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 3.5'],
    keywords='hash database development',
    packages=['digestdb'],
    install_requires=['SQLAlchemy>=1.0.8'],
    extras_require={
        'dev': ['sphinx', 'pep8', 'autopep8'],
        'test': ['coverage'],
    },
)
