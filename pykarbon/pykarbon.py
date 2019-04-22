# -*- coding: utf-8 -*-
'''
Pykarbon is designed to wrap interfacing with the microntroller on the Karbon series in an object,
with the explicit goal of being able to treat this object in a more pythonic manner. In this manner
most serial interactions with carbon are greatly simplified, and are more versatile.
'''
from sys import platform as os_type

import io
import serial

class Karbon:
    '''Handles interactions with both virtual serial ports.

    When initialized, this will scan the systems COM ports for the expected hardware/product id.
    The ports reporting this id are then attached to the class for easy recall and access.

    Attributes:
        ports (:obj:'dict'): The two virtual serial ports enumerated by the MCU.
    '''

    def __init__(self):
        '''Discovers the MCU virtual serial ports'''
        self.ports = {}
        self.get_ports()

    @classmethod
    def write(cls, command, port_name='terminal'):
        '''Takes a command input and interperets it into a serial task.

        Args:
            command (str): String written to serial port
            port_name(str, optional): Select the port to write. Selects terminal by default

        Returns:
            None
        '''
        Interface(port_name).cwrite(command)

    @classmethod
    def read(cls, port_name='terminal', nlines=1, print_output=False):
        '''Get the next line sent from a port

        Args:
            port_name (str, optional): Will read from CAN if 'can' is in the port name.
                Reads from the terminal port by default.
            nlines(int, optional): Number of lines to read from the port
            print_output (bool, optional): Set to false to not print read line

        Returns:
            Raw string or list of raw strings of the lines read from the port
        '''
        output = Interface(port_name).cread(nlines=nlines)

        if print_output:
            for line in output:
                print(line, end='')

        return output

    def get_ports(self) -> dict:
        '''Scans system serial devices and returns the two Karbon serial interfaces

        Returns:
            A dictionary with the keys 'can' and 'terminal' assigned hardware port names.
        '''
        import serial.tools.list_ports as port_list
        all_ports = port_list.comports()

        for port, desc, hwid in sorted(all_ports):
            if "1FC9:00A3" in hwid:

                if 'win' in os_type: #Fix for windows COM ports above 10
                    self.ports[self.check_port_kind(port)] = "\\\\.\\" + port
                else:
                    self.ports[self.check_port_kind(port)] = port

                desc = desc # Remove pylint warning

        return self.ports

    @staticmethod
    def check_port_kind(port_name: str) -> str:
        '''Checks if port is used for CAN or as the terminal

        Args:
            port_name: The hardware device name.

        Returns:
            The kind of port: 'can' or 'terminal'
        '''
        retvl = 'can'

        ser = serial.Serial(port_name, 115200, xonxoff=1, timeout=.1)
        sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser), newline='\r')

        sio.write('version')
        sio.flush()

        if sio.readline():
            retvl = 'terminal'

        return retvl

class Interface(Karbon):
    '''Karbon subclass interface -- controls interactions with the karbon serial interfaces.

    Attributes:
        port: The hardware name of the serial interface
        ser: A serial object connection to the port.
        sio: An io wrapper for the serial object.
        multi_line_response: The number of lines returned when special commands are transmitted.
    '''
    def __init__(self, port_name: str, timeout=.1):
        ''' Opens a connection with the terminal port

        Args:
            port_name: Human-readable name of serial port ("can" or "terminal")
        '''
        super(Interface, self).__init__()
        self.port = self.ports[port_name]
        self.ser = None
        self.sio = None
        self.multi_line_response = {"config" : 12, "status" : 5}
        self.timeout = timeout

    def claim(self):
        '''Claims the serial interface for this instance.'''
        self.ser = serial.Serial(self.port, 115200, xonxoff=1, timeout=self.timeout)
        self.sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser), newline='\r')

    def __enter__(self):
        self.claim()
        return self

    def cwrite(self, command: str):
        '''Writes a command string to the serial terminal and gets the response.

        Args:
            command: Action to be executed on the mcu

        Returns:
            None
        '''

        self.sio.write(command)
        self.sio.flush() # Send 'now'

    def cread(self, nlines=1):
        '''Reads n lines from the serial terminal.

        Args:
            nlines(int, optional): How many lines to try and read

        Returns:
            The combined output of each requested read transaction
        '''
        output = []
        for line in range(0, nlines):
            line = self.sio.readline()
            output.append(line)

        return output

    def release(self):
        '''Release the interface, and allow other applications to use this port'''
        self.ser.close()
        self.sio = None
        self.ser = None

    def __exit__(self, etype, evalue, etraceback):
        self.release()
        return True

    def __del__(self):
        if self.ser:
            self.release()
