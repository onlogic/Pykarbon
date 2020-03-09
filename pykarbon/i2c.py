'''Read and write using the MCUs i2c bus

This module allows you to read and write from any accessible device on the Karbon's I2C bus.
It is not reccommend that you write to any of the existing devices unless you're absolutely certain
of what you're doing.

Note:
    Existing devices:

        K700:
            0x21 -- Onboard PoE
            0x28 -- Modbay PoE (Expansion ONLY)
            0x40 -- Humidity/Temperature Sensor
            0x60 -- Cryptographic Secure Element

        K300:
            0x20 -- Onboard PoE
            0x60 -- Cryptographic Secure Element

Example:

    .. code-block:: python

        import pykarbon.i2c as pki

        device_id = 0x21
        register = 0x99

        dev = pki.Device(device_id)

        val = dev.read(register)

        print("Read {} from {}", val, register)

    This will connect to the microcontroller via the serial interface, and then attempt to read the
    value of register 0x99 from the device at address 0x21.
'''

import pykarbon.hardware as pk


class Device(pk.Interface):
    ''' Opens an I2C device and exposes read/write commands for that device.

    :class:`Device` implements a simple blocking read/write methodology to talk with i2c devices.
    It not neccesary to close one device before opening and using another -- however, you may only
    talk with one device at a time.

    Arguments:
        device_id (int): The device address to read/write.
        timeout (float, optional): The maximum amount of time, in seconds, that the function will
            block while waiting for a response.
    '''

    def __init__(self, device_id, timeout=.05):
        ''' Discovers the correct serial inferface '''
        super().__init__('terminal', timeout=timeout)
        self.device = device_id

    def write(self, reg, data):
        '''Writes data to the selected register

        Args:
            reg  (int): The device register to write.
            data (int): The data to write.

        Returns:
            None if successful, error response if failed
        '''

        write_com = {
            'dev': hex(self.device)[2:],
            'reg': hex(reg)[2:],
            'data': hex(data)[2:],
        }

        command = "i2c w {dev} {reg} {data}".format(**write_com)

        if self.sio is None:
            self.claim()

        self.cwrite(command)

        # Check for error
        resp = self.cread()[0]
        if resp:
            print(resp)

        self.release()

        return resp if resp else None

    def read(self, reg, length=1):
        '''Reads data from the selected register

        Args:
            reg  (int): The device register to read.
            len  (int): The number of bytes (uint8) to read.

        Returns:
            val  (int): The hex value read from the device.
            val  (str): String returned, if any
        '''

        read_com = {
            'dev': hex(self.device)[2:],
            'reg': hex(reg)[2:],
            'length': '00'*round(length),
        }

        command = "i2c r {dev} {reg} {length}".format(**read_com)

        if self.sio is None:
            self.claim()

        self.cwrite(command)

        resp = self.cread()[0]

        self.release()

        try:
            val = int(resp, 16)
        except ValueError:
            val = resp

        return val

    def verified_write(self, reg, data):
        '''Writes data to the selected register and verifies that it was written correctly

        Args:
            reg  (int): The device register to write
            data (int): The data to write

        Returns:
            success (bool): True if passed, False if failed
        '''

        self.write(reg, data)
        out = self.read(reg, length=(len(hex(data)[2:]) / 2))

        return out == data
