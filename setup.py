'''
Setup file that configures the package.
'''
from setuptools import setup

setup(
    name='pykarbon',
    # url='GITHUB_URL'
    author='Jacob Caughfield',
    author_email='jacob.caughfield@logicsupply.com',
    packages=['pykarbon'],
    install_requires=['pyserial'],
    scripts=['scripts/cannit.py'],
    version='0.1',
    license='MIT',
    description='Tools for Karbon hardware interfaces',
    long_description=open('README.rst').read()
)
