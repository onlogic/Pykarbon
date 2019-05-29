''' Discovery and control of hardware interfaces. '''
from sys import platform as os_type

import io
import serial

class Hardware:
    ''' Has methods for performing various hardware tasks: includes port discovery, etc.

    Attributes:
        ports (:obj:'dict'): The two virtual serial ports enumerated by the MCU.
    '''

    def __init__(self):
        ''' Discovers the MCUs two serial ports '''
        self.ports = {}
        self.get_ports()

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

class Interface(Hardware):
    '''Hardware subclass interface -- controls interactions with the karbon serial interfaces.

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

        try:
            self.sio.write(command)
            self.sio.flush() # Send 'now'
        except AttributeError:
            raise Exception("Port is not claimed; must use 'claim' method before 'cwrite' method")

    def cread(self, nlines=1):
        '''Reads n lines from the serial terminal.

        Args:
            nlines(int, optional): How many lines to try and read

        Returns:
            The combined output of each requested read transaction
        '''
        output = []
        try:
            for line in range(0, nlines):
                line = self.sio.readline()
                output.append(line)
        except AttributeError:
            raise Exception("Port is not claimed; must use 'claim' method before 'cread' method")

        return output

    def release(self):
        '''Release the interface, and allow other applications to use this port'''
        try:
            if self.ser:
                self.ser.close()
                self.sio = None
                self.ser = None
        except AttributeError:
            return

    def __exit__(self, etype, evalue, etraceback):
        self.release()
        return True

    def __del__(self):
        self.release()
