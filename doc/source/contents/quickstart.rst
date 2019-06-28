==========
Quickstart
==========

-------------
Prerequisites
-------------

Before running through this guide, make sure you have a couple of things ready:

- A Karbon_ series computer.
- `Python 3`_ downloaded and installed on the system.

    + Make sure you add Python to your path if installing on Windows
- An internet connection on the target K300


------------
Installation
------------

Installing Pykarbon is as simple as opening up a terminal and running:

.. code-block:: console

    > pip install pykarbon --user

or, in Ubuntu:

.. code-block:: console

    $ pip3 install pykarbon --user

-----
Usage
-----

Launch a python terminal using from command line using ``python`` in Windows or ``sudo python3``
in Ubuntu. Now you're just a few commands away from talking with your hardware:

.. code-block:: python

    # Import the module
    >>> import pykarbon.terminal as pkt

    # Start a session
    >>> dev = pkt.Session()

    # Print out configuration information
    >>> dev.update_info(print_info=True)

    # Close the session and release the interface
    >>> dev.close()


.. _Karbon: https://www.logicsupply.com/k300/
.. _Python 3: https://www.python.org/downloads/
