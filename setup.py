'''
Setup file that configures the package.
'''
from setuptools import setup

setup(
    name='pykarbon',
    url='https://github.com/onlogic/Pykarbon',
    author='Logic Supply',
    author_email='jacob.caughfield@logicsupply.com',
    packages=['pykarbon'],
    install_requires=['pyserial'],
    scripts=['scripts/update_firmware.py'],
    version='1.1.2',
    license='BSD-2.0',
    description='Tools for Karbon hardware interfaces.',
    long_description=open('README.rst').read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ]
)
