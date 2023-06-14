'''
Setup file that configures the package.
'''
from setuptools import setup

setup(
    name='pykarbon',
    url='https://github.com/onlogic/Pykarbon',
    author='OnLogic',
    author_email='firmwareengineeringteam@onlogic.com',
    packages=['pykarbon'],
    install_requires=['pyserial>=3.4'],
    scripts=['scripts/update_karbon_firmware'],
    version='1.2.0',
    license='BSD-2.0',
    description='Tools for Karbon hardware interfaces.',
    long_description=open('README.rst').read(),
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ]
)
