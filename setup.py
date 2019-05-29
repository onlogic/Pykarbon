'''
Setup file that configures the package.
'''
from setuptools import setup

setup(
    name='pykarbon',
    url='https://gitlab.logicsupply.com/engineering/karbon/pykarbon_project',
    author='Jacob Caughfield',
    author_email='jacob.caughfield@logicsupply.com',
    packages=['pykarbon'],
    install_requires=['pyserial'],
    scripts=['scripts/update_firmware.py'],
    version='1.0.0',
    license='MIT',
    description='Tools for Karbon hardware interfaces.',
    long_description=open('README.rst').read()
)
