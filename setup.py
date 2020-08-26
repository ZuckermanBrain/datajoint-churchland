#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='churchland-pipeline',
    version='0.0.0',
    description='Datajoint schemas for Mark Churchland lab of Columbia U19',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint>=0.12'],
)