# -*- coding: utf-8 -*-
'''
Pykarbon is designed to wrap interfacing with the microntroller on the Karbon series in an object,
with the explicit goal of being able to treat this object in a more pythonic manner. In this manner
most serial interactions with carbon are greatly simplified, and are more versatile.

Note:

    :class:`pykarbon.pykarbon`'s only class, Karbon, will claim and use both microntroller
    interfaces. Addtionally, the full featuresets of both :class:`pykarbon.terminal.Session` and
    :class:`pykarbon.can.Session` are accessable via :attr:`Karbon.terminal` and
    :attr:`Karbon.can` respectively

Example:

    .. code-block:: python

        import pykarbon.pykarbon as pk

        with pk.Karbon() as dev:
            dev.write(0x123, 0x11223344)  # Send a message over the can interface
            dev.can.data  # List of receive can messages

            # Karbon.write uses input length and types to determine what action to perform!
            dev.write(0, '1')  # Set digital output zero high
'''

import pykarbon.can as pkc
import pykarbon.terminal as pkt


class Karbon:
    '''Handles interactions with both virtual serial ports.

    When initialized, this will scan the systems COM ports for the expected hardware/product id.
    The ports reporting this id are then attached to the class for easy recall and access.

    Attributes:
        can: A pykarbon.can session object -- used to interface with karbon can bus
        terminal: a pykarbon.terminal session object -- used to interface with karbon terminal.
    '''

    def __init__(self, automon=True, timeout=.01, baudrate=None):
        '''Opens a session with the two MCU virtual serial ports

        Arguments:
            automon: Defaults to True -- will cause can and terminal ports to auto-monitored

        '''
        self.can = pkc.Session(automon=automon, timeout=timeout, baudrate=baudrate)
        self.can.autobaud = self.autobaud  # Need to override, as we have lock on terminal

        self.terminal = pkt.Session(automon=automon, timeout=timeout)

    def __enter__(self):
        self.can = self.can.__enter__()
        self.terminal = self.terminal.__enter__()

        return self

    def open(self):
        ''' Opens both ports: Only needs to be called if 'close' has been called '''
        self.can.open()
        self.terminal.open()

    def write(self, *args):
        '''Takes a command input and interperets it into a serial task:

        If given two integer args, it will send a CAN message. If given two string args, it
        will set a terminal parameter. If given an integer as the first arg, and a str as the
        second arg, it will attempt to set the corrospponding digital output.

        A single string argument will simply be sent to the terminal.

        Returns:
            None
        '''
        if len(args) == 1 and isinstance(args[0], str):
            self.terminal.write(args[0])
        elif len(args) == 2:
            if isinstance(args[0], int) and isinstance(args[1], int):
                self.can.write(args[0], args[1])
            elif isinstance(args[0], int) and isinstance(args[1], str):
                self.terminal.set_do(args[0], args[1])
            elif isinstance(args[0], str) and isinstance(args[1], str):
                self.terminal.set_param(args[0], args[1])

    def read(self, port_name='terminal', print_output=False):
        '''Get the next line sent from a port

        Args:
            port_name (str, optional): Will read from CAN if 'can' is in the port name.
                Reads from the terminal port by default.
            print_output (bool, optional): Set to false to not print read line

        Returns:
            Raw string of the line read from the port
        '''
        if 'terminal' in port_name.lower():
            line = self.terminal.readline()
        elif 'can' in port_name.lower():
            line = self.can.readline()

        if print_output:
            print(line)

        return line

    def autobaud(self, baudrate: int) -> str:
        '''Autodetect the bus baudrate

        If the passed argument 'baudrate' is None, the baudrate will be autodetected,
        otherwise, the bus baudrate will be set to the passed value.

        Args:
            baudrate: The baudrate of the bus in thousands. Set to 'None' to autodetect

        Returns:
            The discovered or set baudrate
        '''
        set_rate = None
        if not baudrate:
            self.terminal.write('can-autobaud')
            self.terminal.update_info()
            set_rate = self.terminal.info['can-baudrate']['value']
        else:
            self.terminal.set_param('can-baudrate', str(baudrate))
            set_rate = str(baudrate)

        return set_rate

    def show_info(self):
        '''Updates and prints configuration information'''
        try:
            self.terminal.update_info(print_info=True)
        except TypeError:
            self.terminal.update_info(print_info=True)

    def close(self):
        ''' Close both ports '''
        self.terminal.close()
        self.can.close()

    def __exit__(self, etype, evalue, etraceback):
        self.terminal.__exit__(etype, evalue, etraceback)
        self.can.__exit__(etype, evalue, etraceback)

    def __del__(self):
        self.terminal.__del__()
        self.can.__del__()
