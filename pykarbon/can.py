# -*- coding: utf-8 -*-
''' Tool for running a session with the can interface.

Example:

    .. code-block:: python

        import pykarbon.can as pkc
        from time import sleep

        with pkc.Session() as dev:
            dev.write(0x123, 0x11223344)  # Send a message

            sleep(5)  # Your code here!

            dev.storedata('can_messages')  # Save messages that we receive while we waited

    Lets us autodetect the can bus baudrate, write data to the can bus, wait for some messages to
    be receive, and finally save those messages to can_messages.csv
'''
from time import sleep, time
import threading
import re

import pykarbon.hardware as pk

# Tools --------------------------------------------------------------------------------------------


def stringify(value):
    ''' Takes variously formatted hex values and outputs them in simple string format '''
    out = ''
    if value:
        out = (hex(value) if isinstance(value, int) else value).replace('0x', '').upper()

    return out


def hexify(value):
    ''' Takes variously formatted hex values and outputs them as a int '''
    out = 0x0
    if value:
        out = int(value.replace('0x', ''), 16) if isinstance(value, str) else value

    return out
# --------------------------------------------------------------------------------------------------


class Session():
    '''Attaches to CAN serial port and allows reading/writing from the port.

    Automatically performs port discovery on linux and windows. Then is able to take
    ownership of a port and perform read/write operations. Also offers an intelligent
    method of sending can messages that will automatically determine frame format, type,
    and data length based only on the message id and data.

    There is additional support for registering a function to certain can data ids. When the
    interface receives a registered message, it will call the function and send the returned
    data. This features requires running the session with automonitoring enabled.

    By default, the session will also try to automatically discover the bus baudrate.

    Arguments:
        baudrate (int/str, optional):

            `None` -> Disable setting baudrate altogther (use mcu stored value)

            `'autobaud'` -> Attempt to automatically detect baudrate

            `100 - 1000` -> Set the baudrate to the input value, in thousands

        timeout (float, optional): Time until read/write attempts stop in seconds. (None disables)
        automon (bool, optional): Automatically monitor incoming data in the background.
        reaction_poll_delay (float, optional): Time between checking received data for a registered
            value. Decreasing this delay will consume more unused CPU time.


    If the baudrate option is left blank, the device will instead attempt to automatically
    detect the baudrate of the can-bus. When 'automon' is set to 'True', this object will
    immediately attempt to claim the CAN connection that it discovers. Assuming the connection
    can be claimed, the session will then start monitoring all incoming data in the background.

    This data is stored in the the session's 'data' attribute, and can be popped from the queue
    using the 'popdata' method. Additionally, the entire queue may be purged to a csv file using
    the 'storedata' method -- it is good practice to occasionally purge the queue.

    Attributes:
        interface: :class:`pykarbon.hardware.Interface`
        pre_data: Data before it has been parsed by the registry service.
        data: Queue for holding the data read from the port
        isopen: Bool to indicate if the interface is connected
        baudrate: Reports the discovered or set baudrate
        registry: Dict of registered DIO states and function responses
        bgmon: Thread object of the bus background monintor
    '''
    def __init__(self, baudrate='autobaud', timeout=.01, automon=True, reaction_poll_delay=.01):
        '''Discovers hardware port name.'''
        self.interface = pk.Interface('can', timeout)

        self.poll_delay = reaction_poll_delay
        self.baudrate = None
        self.pre_data = []
        self.data = []
        self.isopen = False
        self.bgmon = None
        self.registry = {}

        if baudrate == 'autobaud':
            self.autobaud(None)
        elif isinstance(baudrate, int):
            self.autobaud(baudrate)

        if automon:
            self.open()
            self.bgmonitor()
        else:
            self.data = self.pre_data

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

        NOTE: Strips EoL characters.

        Args:
            line: Data that will be pushed onto the queue
        '''

        self.data.append(line.strip('\n\r'))

    def autobaud(self, baudrate: int) -> str:
        '''Autodetect the bus baudrate

        If the passed argument 'baudrate' is None, the baudrate will be autodetected,
        otherwise, the bus baudrate will be set to the passed value.

        When attempting to auto-detect baudrate, the system will time-out after 3.5 seconds.

        Args:
            baudrate: The baudrate of the bus in thousands. Set to 'None' to autodetect

        Returns:
            The discovered or set baudrate
        '''
        set_rate = None
        with pk.Interface('terminal', timeout=.001) as term:
            if not baudrate:
                term.cwrite('can-autobaud')

                start = time()
                elapsed = 0

                set_rate = term.cread()[0].strip('\n\r')
                while not set_rate and elapsed < 3.5:
                    set_rate = term.cread()[0].strip('\n\r')
                    elapsed = time() - start
            else:
                term.cwrite('set can-baudrate ' + str(baudrate))
                set_rate = str(baudrate)

        temp = re.search(r'\s(?P<baud>[\d]+)k', set_rate)
        self.baudrate = temp.groupdict()['baud'] if temp else None

        return self.baudrate

    @staticmethod
    def format_message(id, data, **kwargs):
        ''' Takes an id and data and determines other message characteristics

        When keyword arguments are left blank, this function will extrapolate the correct
        frame information based on the characteristics of the passed id and data.
        If desired, all of the automatically determined characteristics may be overwritten.

        Args:
            data_id: Data id of the message, in hex (0x123, '0x123', '123')
            data: Message data, in hex -- if 'None', the device will send a remote frame.
                NOTE: Use string version of hex to send leading zeroes ('0x00C2' or '00C2')
            **kwargs:

                *format*: Use standard or extended frame data id ('std' or 'ext')

                *length*: Length of data to be transmitted, in bytes (11223344 -> 4)

                *type*: Type of frame ('remote' or 'data')
        '''

        data = stringify(data)
        message = {
            'format': kwargs.get('format', 'std' if hexify(id) <= 0x7FF else 'ext'),
            'id': stringify(id),
            'length': kwargs.get('length', int(len(data) / 2)),
            'data': data,
            'type': kwargs.get('type', 'data' if data else 'remote')
        }

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

    def register(self, data_id, action, **kwargs):
        '''Automatically perform action upon receiving data_id

        Register an action that should be automatically performed when a certain data
        id is read. By default the action will be performed when the id is attached
        to any frame type, and the action's returned data will be checked -- if the data
        can be formatted as a can message, it will automatically be transmitted as a reply.

        Actions should be a python function, which will be automatically wrapped in a
        pykarbon.can.Reactions object by this function. When the passed action is called
        Reactions will try to pass it the hex id and data as the first and second positional
        arguments. If thrown a TypeError, it will call the action without any arguments.

        Example:
            >>> Session.register(0x123, action)

        Note:
            If the frame is a remote request frame, the passed data will be 'remote' instead
            of an int!

        Args:
            data_id: The hex data_id that the action will be registered to
            action: The python function that will be performed.
            kwargs:
                remote_only: Respond only to remote request frames (Default: False)
                run_in_background: Run action as background task (Default: True)
                auto_response: Automatically reply with returned message (Default: True)

        Returns:
            The 'Reaction' object that will be used in responses to this data_id
        '''

        reaction = Reactions(self.write, data_id, action, **kwargs)
        self.registry[data_id] = reaction

        return reaction

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

        If no data is read from the port, then nothing is added to the data queue.

        Returns
            The data read from the port
        '''
        line = ""
        if self.isopen:
            line = self.interface.cread()[0]
            if line:
                self.pre_data.append(line)

        return line

    def bgmonitor(self):
        '''Start monitoring the canbus in the background

        Uses python threading module to start the monitoring process.

        Returns:
            The 'thread' object of this background process
        '''

        if not self.data:
            self.data = []

        self.bgmon = threading.Thread(target=self.monitor)
        self.bgmon.start()

        threading.Thread(target=self.registry_service).start()

        return self.bgmon

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

    def registry_service(self):
        '''Check if receive line has a registered action.

        If the receive line does have an action, perform it, and then move the data
        into the main data queue. Otherwise, just move the data.
        '''
        while self.isopen:
            # Allow CPU to have time
            sleep(self.poll_delay)

            try:
                line = self.pre_data.pop(0)
                if line:
                    self.check_action(line)
                    self.pushdata(line)
            except IndexError:
                continue

        return 0

    def check_action(self, line):
        '''Check is message has an action attached, and execute if found

        Args:
            line: Can message formatted as [id] [data]
        '''
        try:
            data_id, message = line.strip('\n\r').split(' ')
        except ValueError:
            return

        data_id = int(data_id, 16)

        if data_id in self.registry:
            reaction = self.registry[data_id]
            if reaction.remote_only and ("remote" not in message):
                return

            if reaction.run_in_background:
                reaction.bgstart(message)
            else:
                reaction.start(message)

        return

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

                line = line.strip('\n\r')

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

        try:
            if self.bgmon.isAlive():
                sleep(.1)
        except AttributeError:
            sleep(.001)

        self.interface.release()

    def __exit__(self, etype, evalue, etraceback):
        self.isopen = False

        try:
            if self.bgmon.isAlive():
                sleep(.1)
        except AttributeError:
            sleep(.001)

        self.interface.__exit__(etype, evalue, etraceback)

    def __del__(self):
        if self.isopen:
            self.close()


class Reactions():
    '''A class for performing automated responses to certain can messages.

    If the action returns a dict of hex id and data, then the reaction will
    automatically respond with this id and data. If the dict has 'None' for
    id, then the reaction will respond with the originating frame's id and
    then returned data.

    Note:
        Example action response: {'id': 0x123, 'data': 0x11223344}

    Attributes:
        data_id: The can data id registered with this reaction
        action: Function called by this reaction
        remote_only: If the reaction will respond to non-remote request frames
        run_in_background: If reaction will run as background thread
        auto_response: If reaction will automatically reply
        canwrite: Helper to write out can messages
    '''
    def __init__(self, canwrite, data_id, action, **kwargs):
        '''Init attributes

        Additonally sets all kwargs to default values if they are not
        explicitly specified.
        '''
        self.canwrite = canwrite
        self.data_id = data_id
        self.action = action

        if 'remote_only' in kwargs:
            self.remote_only = kwargs['remote_only']
        else:
            self.remote_only = False

        if 'run_in_background' in kwargs:
            self.run_in_background = kwargs['run_in_background']
        else:
            self.run_in_background = True

        if 'auto_response' in kwargs:
            self.auto_response = kwargs['auto_response']
        else:
            self.auto_response = True

    def start(self, hex_data):
        '''Run the action in a blocking manner

        Args:
            hex_data: The hex data of the message that invoked this reaction.
                Should be the string 'remote' for remote frames.
        '''
        if not self.remote_only and ('remote' not in hex_data):
            hex_data = int(hex_data, 16) if hex_data else None

        try:
            out = self.action(self.data_id, hex_data)
        except TypeError:
            out = self.action()

        return self.respond(out)

    def bgstart(self, hex_data):
        '''Call start as a background thread

        Returns:
            The thread of the background action
        '''

        bgaction = threading.Thread(target=self.start, args=[hex_data])
        bgaction.start()

        return bgaction

    def respond(self, returned_data):
        '''Automatically respond to frames, if requested

        Args:
            returned_data: A dict of id and data. If None, no response will be sent
        '''
        if (not returned_data) or (not self.auto_response):
            return

        try:
            if not returned_data['id']:
                self.canwrite(self.data_id, returned_data['data'])
            else:
                self.canwrite(returned_data['id'], returned_data['data'])
        except (TypeError, KeyError) as bad_return:
            print("Bad action response: ", bad_return)
            return

        return


def hardware_reference(device='K300'):
    '''Print useful hardware information about the device

    Displays hardware information about the CAN device, such as pinouts.
    Then pinouts assume that the user is facing the front if the device, and that the fins
    are pointed up.

    Args:
        device (str, optional): The karbon series being used. Defaults to the K300
    '''

    ref_k300 = \
        '''
    Info: Compliant with CAN 2.0B. The canbus is not internally terminated; the device
    should be used with properly terminated CAN cables/bus. The termination resistors
    are required to match the nominal impedance of the cable. To meet ISO 11898, this
    resistance should be 120 Ohms.

    Pinout: || GND | CAN_LOW | CAN_HIGH ||
        '''

    ref_dict = {'K300': ref_k300}

    try:
        print(ref_dict[device.upper()])
    except KeyError:
        print("Please select from: [K300]")
