# .py file for setting up ./core as a python package with pip.
from setuptools import setup, find_packages
setup(
    name='AnaloguesCore',
    version='1.2.2',
    author='Sarah Gammon',
    author_email='gammon.sarah@ouranos.ca',
    description='Core module for spatial analogues dashboard app',
    packages=find_packages(include=['core', 'core.*']), 
)