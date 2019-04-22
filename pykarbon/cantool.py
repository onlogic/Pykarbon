# -*- coding: utf-8 -*-
''' Tool for running a session with the can interface '''
import pykarbon.pykarbon as pk

class Session():
    '''Attaches to CAN serial port and allows reading/writing from the port.

    Automatically performs port discovery on linux and windows. Then is able to take
    ownership of a port and perform read/write operations. Also offers an intelligent
    method of sending can messages that will automatically determine frame format, type,
    and data length based only on the message id and data.

    By default, the session will also try to automatically discover the bus baudrate.

    Attributes:
        interface: Serial interface object that has methods for reading/writing to the port.
        data: Queue for holding the data read from the port
        isopen: Bool to indicate if the interface is connected
    '''
    def __init__(self, baudrate=None, timeout=.1):
        '''Discovers hardware port name.

        If the baudrate option is left blank, the device will instead attempt to automatically
        detect the baudrate of the can-bus

        Args:
            baudrate(int, optional): Specify a baudrate, in thousands (500 -> 500K).
            timeout(int, optional): Time until read/write attempts stop in seconds. (None disables)
        '''
        self.interface = pk.Interface('can', timeout)
        self.data = []
        self.isopen = False
        self.autobaud(baudrate)

    def __enter__(self):
        self.interface.__enter__()
        self.isopen = True
        return self

    def open(self):
        '''Claim the interface (only one application may open the serial port)'''
        self.interface.claim()
        self.isopen = True

    def pushdata(self, line: str):
        '''Add data to the end of the session queue.

        NOTE: Does not push empty strings

        Args:
            line: Data that will be pushed onto the queue
        '''

        if line:
            self.data.append(line)

    @staticmethod
    def autobaud(baudrate: int) -> str:
        '''Autodetect the bus baudrate

        If the passed argument 'baudrate' is None, the baudrate will be autodetected,
        otherwise, the bus baudrate will be set to the passed value.

        Args:
            baudrate: The baudrate of the bus in thousands. Set to 'None' to autodetect

        Returns:
            The discovered or set baudrate
        '''
        set_rate = 'Not Set'
        with pk.Interface('terminal') as term:
            if not baudrate:
                term.cwrite('can-autobaud')
                set_rate = term.cread()[0].strip('\r\n')
            else:
                term.cwrite('set can-baudrate ' + str(baudrate))
                set_rate = str(baudrate)

        return set_rate

    @staticmethod
    def format_message(data_id, data, **kwargs):
        ''' Takes an id and data and determines other message characteristics

        When keyword arguments are left blank, this function will extrapolate the correct
        frame information based on the characteristics of the passed id and data.
        If desired, all of the automatically determined characteristics may be overwritten.

        Args:
            data_id(int): Data id of the message, in hex
            data(int): Message data, in hex -- if 'None', the device will send a remote frame.
            **kwargs:
                'format': Use standard or extended frame data id ('std' or 'ext')
                'length': Length of data to be transmitted, in bytes (11223344 -> 4)
                'type': Type of frame ('remote' or 'data')
        '''

        message = {'format': 'std', 'id': data_id, 'length': 0, 'data': data, 'type': 'data'}

        if data_id > 0x7FF:
            message['format'] = 'ext'

        if not data:
            message['type'] = 'remote'
        else:
            message['length'] = len(hex(data)[2:]) / 2

        for key, value in kwargs:
            try:
                message[key] = value
            except KeyError:
                print("{} is not a valid keyword".format(key))

        return message

    def send_can(self, message) -> str:
        '''Transmits the passed message on the canbus

        Args:
            message: A dictionary containing the data required to build a can message

        Returns:
            The string version of the transmitted message
        '''

        str_message = '{format} {id} {length} {data} {type}'.format(**message)
        self.interface.cwrite(str_message)

        return str_message

    def write(self, can_id, data):
        '''Auto-format and transmit message

        Args:
            can_id: The hex id of the data
            data: The hex formatted data
        '''
        message = self.format_message(can_id, data)
        self.send_can(message)


    def readline(self):
        '''Reads a single line from the port, and stores the output in self.data

        If no data is read from the port, then nothing is added to the data queue

        Returns
            The data read from the port
        '''
        line = ""
        if self.isopen:
            line = self.interface.cread()[0]
            self.pushdata(line)

        return line

    def storedata(self, filename: str, mode='a+'):
        '''Pops the entire queue and saves it to a csv.

        By default, it will append to existing filename, and create a non-exisitant one

        Args:
            filename: Name of file that will be created.
            mode(str, optional): The file write mode to be used.
        '''

        if '.csv' not in filename:
            filename = filename + '.csv'

        with open(filename, mode) as datafile:
            while True:
                line = self.popdata()

                if not line:
                    break

                line = line.replace(' ', ',')
                datafile.write(line)

    def popdata(self):
        '''If there is data in the queue, pop an entry and return it.

        Uses queue behavior, so data is returned with 'first in first out' logic

        Returns:
            String of the data read from the port. Returns empty string if the queue is empty
        '''
        try:
            out = self.data.pop(0)
        except IndexError:
            out = ""

        return out

    def close(self):
        '''Release the interface so that other session may interact with it'''
        self.interface.release()
        self.isopen = False

    def __exit__(self, etype, evalue, etraceback):
        self.interface.__exit__(etype, evalue, etraceback)
        self.isopen = False

    def __del__(self):
        pass
