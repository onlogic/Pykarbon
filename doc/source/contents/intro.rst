=====
Intro
=====

--------------------------------
Pykarbon: Hardware Made Possible
--------------------------------

The Pykarbon module provides a set of tools for interfacing with the hardware devices on
OnLogics's 'Karbon' series industrial PCs. These interfaces include the onboard CAN bus,
Digital IO, and a few other hardware devices.

The goal of this package is to provide a simple, but powerful, base platform that will allow
you to quickly and easily integrate a Karbon into your own application.

---------------------
Automatic Operation
---------------------

Getting started with Pykarbon doesn't take a lot of code; many use-cases can be handled in only *five lines:*

.. code-block:: python

  import pykarbon.pykarbon as pk

  with pk.Karbon() as dev:
    dev.write() # Your commands here
    dev.can.data
    dev.terminal.data

This command automatically discovers and prepares your system's hardware interfaces by performing several tasks:

- Discovers the two COM ports owned by your Karbon's microcontroller
- Opens a connection with both ports, and acquires a lock
- Starts background threads for monitoring and processing incoming data
- Attempts to detect the baudrate of connected CAN devices
- Reads configuration information about your microcontroller

All of that setup happens in the background and, once complete, you are free to access configuration settings, the CAN interface, digital IO, and so on.
When the context session ends, the connection will be automatically cleaned up, and the interfaces closed.

-----------
The Toolbox
-----------

Pykarbon offers several modules that grant different levels of access to the hardware. These include:

:ref:`pykarbon.pykarbon`
^^^^^^^^^^^^^^^^^^^^^^^^

This is the highest level module. Its single 'Karbon' class creates a control object that you can
use to write to both the Karbon system's serial terminal and CAN port. It also starts background monitoring
on both of those ports, and allows you to access any data streamed to either port from their
respective data queues. In most cases, the best way to use this module is as a command line
controller for your hardware.

:ref:`pykarbon.core`
^^^^^^^^^^^^^^^^^^^^

This core module provides access to basic commands in a blocking, low-overhead, way.
It is able sniff packets on the CAN bus, read back user configuration information, and toggle digital IO.

:ref:`pykarbon.terminal` & :ref:`pykarbon.can`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The terminal and can modules hold the tools for creating, controlling and monitoring their
respective virtual terminals. They also allow you to disable automatic background monitoring, and
take control of reads and writes in a very direct way.

These modules also provide a "reaction" class that may be subclassed in order to generate your own,
custom, responses to bus events. Reactions have the built-in ability to respond over the port they are
using, and they will automatically execute your self-defined callback function.
This means that you can register *any python function* to be called when a certain message is detected on the bus.

:ref:`pykarbon.hardware`
^^^^^^^^^^^^^^^^^^^^^^^^

The low-level access layer takes care of discovering and claiming ports, and offers an object with
read and write methods. Developers that want fine-grain control over how their system operates, or
who just don't need any bells and whistles, can use this module as a launching point.
