# -*- coding: utf-8 -*-
''' Update the karbon's firmware, given a firmware file '''

import sys
from time import sleep
import pykarbon.hardware as pk

ERR_CD = \
{
    0 : 'Sucess: Firmware Updated!',
    1 : 'Error : Wrong number of arguments.',
    2 : 'Error : Please specify a binary file.',
    3 : 'Error : Could not open firmware file!',
}

def check_file(filename):
    ''' Check if update file is valid '''
    rtval = 0

    if ".bin" not in filename:
        rtval = 2

    try:
        test = open(filename, 'rb')
        test.close()
    except FileNotFoundError:
        rtval = 3

    return rtval

def update_firmware(binary_file):
    ''' Update the K300 firware with specified binary update file '''

    print("Starting update...")

    # Check file is OK
    file_error = check_file(binary_file)
    if file_error:
        return file_error

    print("Launching bootloader...")

    dev = pk.Hardware()

    # Enter the bootloader, if we are in firmware
    if 'terminal' in dev.ports:
        with pk.Interface('terminal') as term:
            term.cwrite('launch-bootloader')

        sleep(1)

    # Claim an interface
    with pk.Interface('can') as bootloader:
        # Perform flash sequence
        flash_seq = ['start', 'erase', 'flash']

        for step in flash_seq:
            print("\r\bPerforming step... " + step, end='')
            bootloader.cwrite(step)

        print("\nFlashing...", end='')
        with open(binary_file, 'rb') as update:
            bootloader.ser.write(update.read())


    print("Done!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(ERR_CD[update_firmware(sys.argv[1])])
    else:
        print(ERR_CD[1])
