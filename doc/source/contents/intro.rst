=====
Intro
=====

--------------------------------
Pykarbon: Hardware Made Possible
--------------------------------

The Pykarbon module provides a set of tools for interfacing with the hardware devices on
Logic Supply's 'Karbon' series industrial PCs. These interfaces include the onboard CAN bus,
Digital IO, and a few other hardware devices.

The goal of this package is to provide a simple, but powerful, base platform that will allow
users to quickly and easily integrate a Karbon into their own application.

---------------------
Automatic Operation
---------------------

``import pykarbon.pykarbon as pk`` is the first thing you will probably encounter when starting up Pykarbon --
and for good reason. This module dead simple to use, but automatically leverages the more powerful
features of Pykarbon's other modules. In fact, the majority of use cases can be boiled down to just
*five lines:*

.. code-block:: python

  import pykarbon.pykarbon as pk

  with pk.Karbon() as dev:
    dev.write() # Your commands here
    dev.can.data
    dev.terminal.data

The *first line alone* does all of the following:

- Discover the two COM ports owned by your Karbon's microcontroller.
- Open a connection with both ports, and acquire a lock.
- Start background threads for monitoring and processing incoming data.
- Attempt to detect the baudrate of connected CAN devices
- Read configuration information about your microcontroller

And the best part is that you really don't need to care what's happening in the background;
all of that complicated setup happens automatically and leaves you free to access your system's
low level hardware in a sane and humane way -- Pykarbon strives to be obvious in this regard.

-----------
The Toolbox
-----------

Pykarbon offers several modules that give you different levels of access and ease when using your
hardware. These include:

:ref:`pykarbon.pykarbon`
^^^^^^^^^^^^^^^^^^^^^^^^

This is the highest level module. It's single 'Karbon' class creates a control object that you can
use to write to both the K300's serial terminal and CAN port. It also starts background monitoring
on both of those ports, and allows you to access any data streamed to either port from their
respective data queues. In most cases, the best way to use this module is as a command line
controller for your hardware.

:ref:`pykarbon.core`
^^^^^^^^^^^^^^^^^^^^

For when you just need the simple things in life, this module is there to let you perform basic
commands in a blocking, hassle-free, way. You can use it to sniff packets on your CAN bus, read
back user configuration information, and toggle digital IO to your heart's content.

:ref:`pykarbon.terminal` & :ref:`pykarbon.can`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The terminal and can modules hold the tools for creating, controlling and monitoring their
respective virtual terminals. They also allow you to disable automatic background monitoring, and
take control of reads and writes in a very direct way.

These modules also provide a "reaction" class that may be subclassed in order to generate your own,
custom, responses to bus events. Reactions have the built-in ability to respond over the port they are
using, but the real power is that they will automatically execute your self-defined callback
function. This means that you can register *any python function* to be called when a certain message
is detected on the bus.

:ref:`pykarbon.hardware`
^^^^^^^^^^^^^^^^^^^^^^^^

The low-level access layer takes care of discovering and claiming ports, and offers an object with
read and write methods. Developers that want fine-grain control over how their system operates, or
who just don't need any bells and whistles, can use this module as a launching point.
