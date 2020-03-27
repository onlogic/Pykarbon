===============
Pykarbon Module
===============
For the full rundown, read `the rest of the docs <https://pykarbon.readthedocs.io/en/latest/>`_.

-----------
What is it?
-----------

The Pykarbon module provides a set of tools for interfacing with the hardware devices on
OnLogic's 'Karbon' series industrial PCs. These interfaces include the onboard CAN bus,
Digital IO, and a few other hardware devices.

The goal of this package is to provide a simple, but powerful, base platform that will allow
users to quickly and easily integrate a Karbon into their own application.

*The tools in this package are designed to work with specific hardware;
this will not work for more generalized projects*

----------------
How do I use it?
----------------

*You will need to install python 3 prior to following this guide.*

Getting started with pykarbon takes only a few minutes:

.. role:: bash(code)
   :language: bash

- Open up a terminal, and run :bash:`pip install pykarbon`

  + On some systems you may need to run as admin, or use the :bash:`--user` flag

- Launch a python shell with :bash:`python`

  + Usually linux users do not have write access to serial ports; grant your user permanent access with :bash:`usermod -a -G dialout $USER` or use :bash:`sudo python`

.. role:: python(code)
   :language: python

- Import pykarbon with :python:`import pykarbon.pykarbon as pk`
- And finally create a control object using :python:`dev = pk.Karbon()`

If all went well, you should now be ready to control a variety of systems, but for now, let's just print out some
configuration information:

- :python:`dev.show_info()`

And close our session:

- :python:`dev.close()`

-------------------
What else can I do?
-------------------

Pykarbon offers a number of tools for automating and using Karbon series hardware interfaces. These include:

- CAN and DIO background data monitoring
- Exporting logged data to .csv
- Registering and making function calls based on these bus events:

  + CAN data IDs
  + Digital Input Events
  + DIO Bus States (Allows partial states)

- Automated can message response to registered IDs
- Automated setting of Digital Output states
- Automatic CAN baudrate detection
- Updating user configuration information:

  + Ignition sense enable/disable
  + Power timing configurations
  + Low battery shutdown voltage
  + Etc.

- Firmware update

Additonally, as Pykarbon's CAN and Terminal sessions must connect to device serial ports, functionality has been added
to allow running these sessions using a context manager:

.. code-block:: python

    import pykarbon.pykarbon as pk
    import pykarbon.can as pkc

    with pk.Karbon() as dev:
        dev.show_info()

    with pkc.Session() as dev:
        dev.write(0x123, 0x11223344)


-------------------------------
A Simple Example: Pykarbon.Core
-------------------------------

.. code-block:: python

    import pykarbon.core as pkcore

    # Set up interfaces:
    can = pkcore.Can()
    term = pkcore.Terminal()

    # Claim the serial ports for use:
    can.claim()
    term.claim()

    # Configure the can baudrate, and view that config
    term.command('set can-baudrate 800')

    print("\nRead User Configuration:")
    term.print_command('config')

    # Write a message, and then listen for and print responses
    can.send(0x123, 0x11223344)

    print("\nMonitoring CAN Bus, Press CTRL+C to Stop!")
    can.sniff() # Will block until you exit with ctrl+c

    # Close the ports!
    can.release()
    term.release()
