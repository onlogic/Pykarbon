''' A set of core functions for when you don't need anything fancy '''
from time import time as mt
import re

import pykarbon.hardware as pk


class Terminal(pk.Interface):
    ''' Exposes methods for blocking read/write control of the serial terminal '''

    def __init__(self, timeout=.05, max_poll=100):
        ''' Initialize the terminal: claim the interface and initialize parameters

        Arguments:
            timeout (float, optional): The maximum amount of time, in seconds, that functions will
                block while waiting for a response.
            max_poll (int, optional): The hard maximum on number of times the system will poll with
                receiving any response. Puts a hard-cap on timeout.

        Parameters:
            voltage (float): The last read system voltage, initialized to 0
        '''

        super().__init__('terminal', timeout=.01)
        self.poll_times = min([int(timeout / .01), max_poll])

        self.voltage = 0
        self.last_input_states = ['-', '-', '-', '-']

    def __enter__(self):
        super().__enter__()
        return self

    def write(self, command):
        return self.cwrite(command)

    def read(self):
        return self.cread()[0].strip('\n\r')

    def readall(self, container):
        ''' Read lines until they stop coming, and save them into a container

            Arguments:
                container (list): List that each line of response will be appended to. It is both
                    passed in and returned so it can be pre-loaded.
        '''
        poll = 0
        while poll < self.poll_times:
            out = self.read()
            if out:
                poll = 0
                container.append(out)
            else:
                poll += 1

        return container if container else ['']

    def grepall(self, expression, default=None):
        ''' Calls readall and returns the first output of a re.search of the output.

        Arguments:
            expression(str): The regular expression to match against
            default(optional): What to return if findall fails, default None
        '''
        out = re.search(expression, self.readall([])[0])
        return out[0] if out else default

    def cleanout(self):
        ''' Flush the input buffer, discarding the contents '''
        return self.ser.reset_input_buffer()

    def print_command(self, command):
        ''' Calls 'command' and prints the output '''
        for item in self.command(command):
            print(item)

    def command(self, command):
        ''' Writes a literal command and returns the result

        Arguments:
            command(str): String that will be written to the serial terminal
        '''
        self.cleanout()

        self.write(command)
        return self.readall([])

    def update_voltage(self):
        ''' Reads updated voltage and parses it into a float '''
        self.cleanout()

        self.write('get-voltage')
        self.voltage = float(self.grepall(r'[\d]+\.[\d]+', 0))

        return self.voltage

    def set_high(self, pin):
        ''' Sets the given digital output high

        Arguments:
           pin(int): 0-3, the index of digital output to set high.
        '''
        state = '----'
        return self.write('set-do ' + state[0:pin] + '1' + state[pin + 1:])

    def set_low(self, pin):
        ''' Sets the given digital output low

        Arguments:
            pin(int): 0-3, the index of digital output to set low.
        '''
        state = '----'
        return self.write('set-do ' + state[0:pin] + '0' + state[pin + 1:])

    def get_state(self, pin):
        ''' Returns the current state of a given digital input,
        updates only that state.

        Arguments:
            pin(int): 0-3, the digital input to read
        '''
        self.cleanout()
        self.write('dio-state')

        out = self.grepall(r'^[0-1]{4}', '----')
        self.last_input_states[pin] = out[pin]

        return out[pin]

    def input_states(self):
        ''' Returns the current state of every single input,
            and updates all stored states
        '''
        self.cleanout()
        self.write('dio-state')

        out = self.grepall(r'^[0-1]{4}', '----')
        temp = []
        for index, item in enumerate(out):
            temp.append(item)
            self.last_input_states[index] = item

        return temp


class Can(pk.Interface):
    ''' Exposes methods for blocking read/write control of the serial terminal '''

    def __init__(self):
        ''' Initialize the terminal: claim the interface and initialize parameters

        Parameters:
            messages(list): List of read messages
        '''

        super().__init__('can', timeout=.01)

        self.messages = []

    def __enter__(self):
        super().__enter__()
        return self

    def send(self, data_id, data, length=None):
        ''' Send a can message.

        Message properties will be inferred from id and data.

        Arguments:
            data_id(int): Hex value data id. If it is larger that 0x7FF, the message
                will be transmitted as CAN 2.0B (extended) format
            data(int): Hex valued data. Message length will be dervived from this. If the
                data is None, a remote request frame will be sent instead.
            length(int): Length in bytes of expected message, should be specified for remote.
        '''
        data_n = hex(data)[2:] if data else 'FF'
        message = {
            'format': 'std' if data_id < 0x7FF else 'ext',
            'id': hex(data_id)[2:],
            'data': data_n,
            'len': str(length) if length else str(int(len(data_n) / 2)),
            'type': 'data' if data else 'remote'
        }
        self.cwrite('{format} {id} {len} {data} {type}'.format(**message))

        return message

    @staticmethod
    def pretty_print(line, prev_time):

        newtime = mt()
        delta = newtime - prev_time
        out = re.search(r'(?P<id>.+)\s(?P<data>.+)', line)

        message = {
            'id': out['id'],
            'data': out['data'],
            'delta': delta
        }

        print('| {delta:010.4f} | 0x{id:8s} | 0x{data:8s} |'.format(**message))

        return newtime, message

    def sniff(self):
        ''' Read messages and print, until stopped. Messages will be saved'''
        print("Listening for CAN messages...")
        print(" ----------------------------------------------")
        print("| Delta      | Id         | Data               |")
        prev = mt()
        while True:
            try:
                line = self.cread()[0].strip('\r\n')
                if line:
                    prev, message = self.pretty_print(line, prev)
                    self.messages.append(message)
                else:
                    pass
            except KeyboardInterrupt:
                print(" ----------------------------------------------")
                break
