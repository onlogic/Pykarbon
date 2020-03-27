==========
Quickstart
==========

-------------
Prerequisites
-------------

Before running through this guide, make sure you have these things ready:

- *A Karbon_ series computer.*
- `Python 3`_ downloaded and installed on the system.

    + Make sure you add Python to your path if installing on Windows
- An internet connection on the target Karbon.


------------
Installation
------------

Installing Pykarbon is as simple as opening up a terminal and running:

.. code-block:: console

    > pip install pykarbon --user

or, in Ubuntu:

.. code-block:: console

    $ python3 -m pip install pykarbon --user

-----
Usage
-----

Launch a Python REPL in your terminal with ``python`` in Windows or ``sudo python3``
in Ubuntu. Now you're just a few commands away from talking with your hardware:

.. code-block:: python

    # Import the module
    import pykarbon.core as pkcore

    # Open a terminal session and print out your firmware version
    with pkcore.Terminal() as dev:
        dev.print_command('version')

    # Open an can session and start listening for packets
    with pkcore.Can() as dev:
        dev.sniff()

In the example above, we used :ref:`pykarbon.core` as a simple, and basic, interface tool. More
advanced and useful features can be found by using the dedicated :ref:`pykarbon.can` and
:ref:`pykarbon.terminal` modules. You can read more about them, and see some examples in the API.


.. _Karbon: https://www.logicsupply.com/catalogsearch/result/?q=Karbon
.. _Python 3: https://www.python.org/downloads/
