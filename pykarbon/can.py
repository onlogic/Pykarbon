# -*- coding: utf-8 -*-
''' Tool for running a session with the can interface '''
from time import sleep
import threading

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
    def __init__(self, baudrate=None, timeout=.1, automon=True):
        '''Discovers hardware port name.

        If the baudrate option is left blank, the device will instead attempt to automatically
        detect the baudrate of the can-bus. When 'automon' is set to 'True', this object will
        immediately attempt to claim the CAN connection that it discovers. Assuming the connection
        can be claimed, the session will then start monitoring all incoming data in the background.

        This data is stored in the the session's 'data' attribute, and can be popped from the queue
        using the 'popdata' method. Additionally, the entire queue may be purged to a csv file using
        the 'storedata' method -- it is good practice to occasionally purge the queue.

        Args:
            baudrate(int, optional): Specify a baudrate, in thousands (500 -> 500K).
            timeout(int, optional): Time until read/write attempts stop in seconds. (None disables)
            automon(bool, optional): Automatically monitor incoming data in the background.
        '''
        self.interface = pk.Interface('can', timeout)
        self.data = []
        self.isopen = False
        self.autobaud(baudrate)
        self.bgmon = None

        if automon:
            self.open()
            self.bgmonitor()

    def __enter__(self):
        if not self.isopen:
            self.interface.__enter__()
            self.isopen = True

        return self

    def open(self):
        '''Claim the interface (only one application may open the serial port)'''
        if not self.isopen:
            self.interface.claim()
            self.isopen = True

        return self.isopen

    def pushdata(self, line: str):
        '''Add data to the end of the session queue.

        NOTE: Does not push empty strings, and strips EoL characters.

        Args:
            line: Data that will be pushed onto the queue
        '''

        if line:
            self.data.append(line.strip('\n\r'))

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
                set_rate = term.cread()[0].strip('\n\r')
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

        message['id'] = hex(data_id)[2:]

        if not data:
            message['type'] = 'remote'
        else:
            data = hex(data)[2:]
            message['length'] = int(len(data) / 2)
            message['data'] = data

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

        # Encourage io to actually send packets
        sleep(.0001)

        return str_message

    def write(self, can_id, data):
        '''Auto-format and transmit message

        For the large majority of use cases, this is the simplest and best method to send a packet
        of data over the canbus. Only message id and the data need to specified as hex values. All
        other information about the packet will be extrapolated.

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

    def bgmonitor(self):
        '''Start monitoring the canbus in the background

        Uses python threading module to start the monitoring process.

        Returns:
            The 'thread' object of this background process
        '''

        bus_monitor = threading.Thread(target=self.monitor)
        bus_monitor.start()
        self.bgmon = bus_monitor

        return bus_monitor

    def monitor(self):
        '''Watches port for can data while connection is open.

        The loop is predicated on the connection being open; closing the connection will stop the
        monitoring session.

        Args:
            session: A canbus session object

        Returns:
            The method used to stop monitoring. (str)
        '''
        retvl = "SessionClosed"
        while self.isopen:
            try:
                self.readline()
            except KeyboardInterrupt:
                retvl = "UserCancelled"

        return retvl

    def storedata(self, filename: str, mode='a+'):
        '''Pops the entire queue and saves it to a csv.

        This method clears the entire queue: once you have called it, all previously received
        data will no longer be stored in the sessions 'data' attribute. Instead, this data will
        now reside in the specified .csv file.

        Each received can message has its own line of the format: id,data.

        By default, if a file that already exists is specified, the data will append to the end of
        this file. This behavior can be changed by setting 'mode' to any standard 'file.write' mode.

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
                datafile.write(line + "\n")

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
        '''Release the interface so that other session may interact with it

        Any existing background monitor session will also be closed. If this session re-opens the
        connection, background monitoring will need to be manually restarted with the 'bgmonitor'
        method.
        '''
        self.isopen = False
        while self.bgmon.isAlive():
            sleep(.001)
        self.interface.release()

    def __exit__(self, etype, evalue, etraceback):
        self.isopen = False
        while self.bgmon.isAlive():
            sleep(.001)
        self.interface.__exit__(etype, evalue, etraceback)

    def __del__(self):
        pass
