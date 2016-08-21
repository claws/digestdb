#!/usr/bin/env python3

''' Installation script for digestdb. '''

import os
import re

from pip.req import parse_requirements
from pip.download import PipSession
from setuptools import setup


install_reqs = parse_requirements("requirements.txt", session=PipSession())
requires = [str(ir.req) for ir in install_reqs]

short_description = (
    'Digestdb provides database style (e.g. SQL) access to binary data'
    'files stored in a balanced set of file system directories.')

long_description = short_description

here = os.path.abspath(os.path.dirname(__file__))


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*['\"](\d\d\.\d\d\.\d+)['\"]")
    init_file = os.path.join(
        os.path.dirname(__file__), 'digestdb', '__init__.py')
    with open(init_file) as f:
        for line in f:
            match = regexp.match(line)
            if match:
                return match.group(1)
        else:
            raise RuntimeError(
                'Cannot find __version__ in digestdb/__init__.py')

version = read_version()

setup(
    name='digestdb',
    version=version,
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
    install_requires=requires,
)
