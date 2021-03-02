#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path
import sys

min_py_version = (3, 5)

if sys.version_info <  min_py_version:
    sys.exit('DataJoint is only supported for Python {}.{} or higher'.format(*min_py_version))

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'requirements.txt')) as f:
    requirements = f.read().split()

setup(
    name='datajoint-churchland',
    version='1.0.1',
    description='Datajoint schemas for Mark Churchland lab of Columbia U19',
    author='Najja Marshall',
    author_email='njm2149@columbia.edu',
    packages=find_packages(exclude=[]),
    install_requires=requirements,
    python_requires='~={}.{}'.format(*min_py_version)
)


