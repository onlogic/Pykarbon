# -*- coding: utf-8 -*-
''' Tools for sending commands to the microcontroller, as well as using the DIO

Example:

    .. code-block:: python

        import pykarbon.terminal as pkt

        with pkt.Session() as dev:
            dev.update_info(print_info=True) # Update and print configuration info

            dev.set_do(0, True) # Set digital output zero high

    This snippet will update and print the microntrollers configuration information, and then set
    digital output zero high.
'''
from time import sleep, time
import re
import threading

import pykarbon.hardware as pk


class Session():
    '''Attaches to terminal serial port and allows reading/writing from the port.

    Automatically performs port discovery on linux and windows. Then is able to take
    ownership of a port and perform read/write operations. Also offers a method for setting
    various mcu control properties.

    There is additional support for registering a function to certain DIO states, or input pin
    transitions. When the interface receives a registered event, it will call the function and
    optionally set the digital outputs to the returned state.
    This features requires running the session with automonitoring enabled.

    Digital IO events will be recorded in the data queues, while configuration information will
    overwite the 'info' dictionary.

    Args:
        timeout(int, optional): Time until read attempts stop in seconds. (None disables)
        automon(bool, optional): Automatically monitor incoming data in the background.

    When 'automon' is set to 'True', this object will immediately attempt to claim the terminal
    connection that it discovers. Assuming the connection can be claimed, the session will then
    start monitoring all incoming data in the background.

    This data is stored in the the session's 'data' attribute, and can be popped from the queue
    using the 'popdata' method. Additionally, the entire queue may be purged to a csv file using
    the 'storedata' method -- it is good practice to occasionally purge the queue.

    Attributes:
        interface: :class:`pykarbon.hardware.Interface`
        pre_data: Data before it has been parsed by the registry service.
        data: Queue for holding the data read from the port
        isopen: Bool to indicate if the interface is connected
        info: Dictionary of information about the configuration of the mcu.
        registry: Dict of registered DIO states and function responses
        bgmon: Thread object of the bus background monintor
    '''
    def __init__(self, timeout=.01, automon=True):
        '''Discovers hardware port name. '''
        self.interface = pk.Interface('terminal', timeout)

        self.pre_data = []
        self.data = []
        self.isopen = False

        self.info = {
            'version':
                {
                    'value': None,
                    'desc': 'Firmware version number.'
                },
            'build':
                {
                    'value': None,
                    'desc': 'Firmware build date.'
                },
            'configuration':
                {
                    'value': None,
                    'desc': 'Current user configuration.'
                },
            'ignition-sense':
                {
                    'value': None,
                    'desc': 'If ignition sensing is enabled or disabled.'
                },
            'startup-timer':
                {
                    'value': None,
                    'desc': 'Time, in seconds, until boot after ignition on.'
                },
            'shutdown-timer':
                {
                    'value': None,
                    'desc': 'Time, in seconds, until soft power off after ignition off.'
                },
            'hard-off-timer':
                {
                    'value': None,
                    'desc': 'Time, in seconds, until hard power off after igntion off.'
                },
            'auto-power-on':
                {
                    'value': None,
                    'desc': 'Force device to power on when first connected to AC power.'
                },
            'shutdown-voltage':
                {
                    'value': None,
                    'desc': 'Voltage when device will power off to avoid battery discharge.'
                },
            'hotplug':
                {
                    'value': None,
                    'desc': 'Set if the display port outputs are hotpluggable.'
                },
            'can-baudrate':
                {
                    'value': None,
                    'desc': 'Current CAN bus baudrate.'
                },
            'dio-power-switch':
                {
                    'value': None,
                    'desc': 'Have digital inputs act as a remote power switch when device is off.'
                },
            'boot-config':
                {
                    'value': None,
                    'desc': 'If the current configuration will be loaded at boot.'
                },
            'voltage':
                {
                    'value': None,
                    'desc': 'The last-read system input voltage'
                }
        }

        self.bgmon = None
        self.registry = {}

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

        NOTE: Does not push empty strings, and strips EoL characters.

        Args:
            line: Data that will be pushed onto the queue
        '''

        self.data.append(line)

    def register(self, input_num, state, action, **kwargs):
        '''Automatically perform action upon receiving data_id

        Register an action that should be automatically performed when a certain digital input
        state is read. By default, this action will only be performed when the digital input
        first transitions to a state -- subsequent bus reads will be ignored:

        Example:
            >>> Session.register(1, 'low', action)

            Input 1 : 1 --> 0   (*Execute Action*)

            Input 1 : 0 --> 0   (*Do nothing*)

            Input 1 : 0 --> 1   (*Do nothing*)

            Input 1 : 1 --> 0   (*Execute Action*)

        Actions should be a python function, which will be automatically wrapped in a
        pykarbon.terminal.Reactions object by this function. When the passed action is called
        Reactions will try to pass it the current dio state as the first positional argument.
        If thrown a TypeError, it will call the action without any arguments.

        There is addtional support for masking input events with a particular bus state. That
        is, if an input event occurs, but the bus does not match the state, the action will
        not be executed.

        Example:
            >>> Session.register(1, 'high', action, dio_state='---0 ---1')

            Input 1 : 0 --> 1, Bus State: 0011 1111   (*Do nothing*)

            Input 1 : 1 --> 1, Bus State: 0000 1111   (*Do nothing*)

            Input 1 : 1 --> 0, Bus State: 0000 1111   (*Do nothing*)

            Input 1 : 0 --> 1, Bus State: 0000 1111   (*Execute Action*)

        Note:
            Bus state format is digital output 0-4 space digital input 0-4. Dashes are 'don't care'

        Args:
            dio_state(str) : Shorthand for the state of the dio, a dash will ignore the value.
            action: The python function that will be performed.
            kwargs:
                transition_only: Act only when a state is true by transition (Default: True)
                dio_state: Mask performing action with dio state (Default: ---- ----)
                run_in_background: Run action as background task (Default: True)
                auto_response: Automatically reply with returned message (Default: True)

        Returns:
            The 'Reaction' object that will be used in responses to this data_id
        '''

        reaction = Reactions(self.set_all_do, [input_num, state], action, **kwargs)
        self.registry[input_num] = {state: reaction}

        return reaction

    def print_info(self):
        ''' Prints out mcu configuration information '''
        top_bot = "-"
        top_bot = top_bot.rjust(37, '-')
        print(top_bot)
        for key in self.info:
            temp_key = key.ljust(18, ' ')
            try:
                temp_val = self.info[key]['value'][0:10].ljust(12, ' ')
                print("+  {}|  {}+".format(temp_key, temp_val))
            except TypeError:
                pass
        print(top_bot)

    def update_info(self, print_info=False):
        ''' Request configuration information from MCU

        Arguments:
            print(bool, optional): Print out info after update. (Default: False)
        '''

        if self.isopen:
            self.interface.cwrite('version')
            self.interface.cwrite('config')
            # Don't update voltage b/c of version limitations
            if print_info:
                sleep(1)
                self.print_info()

    def set_param(self, parameter: str, value: str, update=True, save_config=True):
        ''' Sets a mcu configuration parameter

        Arguments:
            parameter: Paramter to change
            value: Parameter will be set to this value
            update: Call update info to reflect param changes

        Returns:
            one or zero to indicate sucess or failure
        '''
        retvl = 0
        if self.isopen:
            self.interface.cwrite('set {} {}'.format(parameter, value))
            if update:
                sleep(.1)  # Needs time to process
                self.update_info()
            if save_config:
                sleep(.1)  # Needs time to process
                self.interface.cwrite('save-config')
        else:
            retvl = 1

        return retvl

    def set_do(self, number, state):
        ''' Set the state of a single digital output

        Maps different input formats into a unified format, and then calls a write method that sets
        a single output.

        Example:
            >>> set_do(0, True)
            >>> set_do('two', 0)
        '''
        states = {'zero': '-', 'one': '-', 'two': '-', 'three': '-'}
        map_state = {0: '0', 1: '1', False: '0', True: '1', '0': '0', '1': '1'}
        map_numbr = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 'zero': 'zero',
                     'one': 'one', 'two': 'two', 'three': 'three'}

        states[map_numbr[number]] = map_state[state]
        self.write('set-do {zero}{one}{two}{three}'.format(**states))

    def set_all_do(self, states):
        ''' Sets all digital outputs based on a list of states

        Arguments:
            states (list): A list of '1', '0', or '-' corrospponding to the state of each output.
                Note: A '-' will skip setting the corrosponding output

        Example:
            >>> set_all_do(['0', '0', '0', '0'])  # turn all outputs off
        '''
        self.write("set-do {}{}{}{}".format(*states))

    def parse_line(self, line):
        ''' Parse a non-dio line into mcu configuration info '''
        line = line.strip("\n\r")

        if 'err' in line.lower():
            print(line)
            return line

        found_match = True
        if '<' in line:
            version, build = line.split('|')
            self.info['version']['value'] = version.strip('<').strip(' ')
            build = build
            self.info['build']['value'] = build.strip('>').strip(' ')
        elif 'Boot' in line:
            try:
                self.info['boot-config']['value'] = line.split(':')[1].strip(' ')
            except IndexError:
                print("Unexpected response: " + line)
        elif 'Remote' in line:
            try:
                self.info['dio-power-switch']['value'] = line.split(':')[1].strip(' ')
            except IndexError:
                print("Unexpected response: " + line)
        else:
            found_match = False

        if not found_match:
            for key in self.info:
                if key in line.lower().replace(' ', '-'):
                    try:
                        self.info[key]['value'] = line.split(':')[1].strip(' ')
                    except IndexError:
                        print("Unexpected response: " + line)

        return line

    def update_voltage(self, timeout=2):
        ''' Update the system input voltage

        Arguments:
            timeout (optional): Set how long, in seconds to wait for voltage readout.
        '''
        old_voltage = self.info['voltage']['value']
        self.info['voltage']['value'] = None
        self.write('get-voltage')

        start = time()
        elapsed = 0
        while not self.info['voltage']['value'] and elapsed < timeout:
            elapsed = time() - start

        if not self.info['voltage']['value']:
            self.info['voltage']['value'] = old_voltage
            return "WARNING: Did not update voltage! Last read: " + str(old_voltage)
        else:
            return self.info['voltage']['value']

    def write(self, command):
        ''' Write an arbitrary string to the serial terminal '''
        self.interface.cwrite(command)

    def readline(self):
        '''Reads a single line from the port, and stores the output in self.data

        If no data is read from the port, then nothing is added to the data queue.

        Returns
            The data read from the port
        '''
        line = ""
        if self.isopen:
            line = self.interface.cread()[0]
            dio_check = re.match(r'[0-1]{4} {0,1}[0-1]{4}', line)
            if dio_check:
                self.pre_data.append(line[0:4] + ' ' + line[4:8])
            elif line:
                self.parse_line(line)

        return line

    def bgmonitor(self):
        '''Start monitoring the terminal in the background

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
        '''Watches port for incoming data while connection is open.

        The loop is predicated on the connection being open; closing the connection will stop the
        monitoring session.

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
            try:
                line = self.pre_data.pop()
                if line:
                    self.pushdata(line)
                    self.check_action(line)
            except IndexError:
                continue

        return 0

    def check_action(self, line):
        '''Check is message has an action attached, and execute if found

        Args:
            line: Dio state formatted as '[0-1]{4} [0-1]{4}'
            prev_line: The previously known state of the bus
        '''

        prev_state = self.get_previous_state(-2)
        state_map = {'1': 'high', '0': 'low'}

        # Check registry against current state of each digital input
        for input_num in self.registry:
            input_state = state_map[line[input_num]]
            transition = state_map[prev_state[input_num]] != input_state

            action = self.registry[input_num].get(input_state)

            if not action:
                continue

            if action.transition_only and not transition:
                continue

            if not re.match(action.dio_state.replace('-', '.'), line):
                continue

            if action.run_in_background:
                action.bgstart(line)
            else:
                action.start(line)

        return

    def get_previous_state(self, index=-1):
        ''' Returns the previous state of the digital io '''
        try:
            prev_line = self.data[index]
        except IndexError:
            prev_line = '1111 0000'

        return prev_line

    def storedata(self, filename: str, mode='a+'):
        '''Pops the entire queue and saves it to a csv.

        This method clears the entire queue: once you have called it, all previously received
        data will no longer be stored in the sessions 'data' attribute. Instead, this data will
        now reside in the specified .csv file.

        Each received dio event has its own line of the format: outputs,inputs.

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
            if self.bgmon.is_alive():
                sleep(.1)
        except AttributeError:
            sleep(.001)

        self.interface.release()

    def __exit__(self, etype, evalue, etraceback):
        self.isopen = False

        try:
            if self.bgmon.is_alive():
                sleep(.1)
        except AttributeError:
            sleep(.001)

        self.interface.__exit__(etype, evalue, etraceback)

    def __del__(self):
        if self.isopen:
            self.close()


class Reactions():
    '''A class for performing automated responses to certain dio transitions.

    If the action returns a list digital output states, then the reaction
    will set each of these states. If the action returns None, no digital
    outputs will be set.

    Example:
        >>> ['0', '1', '1', '0'] # Example action response

    Note:
        When manually building reactions, you will need to pass in a pointer to the set_all_do
        function of a claimed interface.

    Attributes:
        info: The input number and state that trigger this reaction
        dio_state: Mask reaction to this dio state
        action: Function called by this reaction
        transition_only: If the reaction will respond to non-transition events
        run_in_background: If reaction will run as background thread
        auto_response: If reaction will automatically reply
        set_do: Helper to set digital output state
    '''
    def __init__(self, set_all_do, info, action, **kwargs):
        '''Init attributes

        Additonally sets all kwargs to default values if they are not
        explicitly specified.
        '''
        self.set_do = set_all_do
        self.info = info
        self.action = action

        if 'dio_state' in kwargs:
            self.dio_state = kwargs['dio_state']
        else:
            self.dio_state = '---- ----'

        if 'transition_only' in kwargs:
            self.transition_only = kwargs['transition_only']
        else:
            self.transition_only = False

        if 'run_in_background' in kwargs:
            self.run_in_background = kwargs['run_in_background']
        else:
            self.run_in_background = True

        if 'auto_response' in kwargs:
            self.auto_response = kwargs['auto_response']
        else:
            self.auto_response = True

    def start(self, current_state):
        '''Run the action in a blocking manner

        Args:
            current_state: The current state of the dio
        '''

        try:
            out = self.action(current_state)
        except TypeError:
            out = self.action()

        return self.respond(out)

    def bgstart(self, current_state):
        '''Call start as a background thread

        Returns:
            The thread of the background action
        '''

        bgaction = threading.Thread(target=self.start, args=[current_state])
        bgaction.start()

        return bgaction

    def respond(self, returned_data):
        '''Automatically respond to frames, if requested

        Args:
            returned_data: A list of DIO states. If none, no states will be set
        '''
        if (not returned_data) or (not self.auto_response):
            return

        try:
            self.set_do(returned_data)
        except (TypeError, KeyError) as bad_return:
            print("Bad action response: ", bad_return)
            return

        return


def hardware_reference(device='K300'):
    '''Print useful hardware information about the device

    Displays hardware information about the DIO device, such as pinouts.
    Then pinouts assume that the user is facing the front if the device, and that the fins
    are pointed up.

    Args:
        device (str, optional): The karbon series being used. Defaults to the K300
    '''

    ref_k300 = \
        '''
    Info: Isolated digital input/ouput. To function properly, dio should be connect to
    external power and grund.

    Pinout: || GND | DO_1 | DO_2 | DO_3 | DO_4 | DI_1 | DI_2 | DI_3 | DI_4 | PWR ||
        '''

    ref_dict = {'K300': ref_k300}

    try:
        print(ref_dict[device.upper()])
    except KeyError:
        print("Please select from: [K300]")
