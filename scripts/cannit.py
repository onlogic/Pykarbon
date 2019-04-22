'''Opens and runs a basic CAN interface session'''

import asyncio
from pykarbon import cantool

async def readcan(session):
    ''' An 'awaitable' readline wrapper.

    Allows code to continue execution while waiting for read task to return

    Args:
        session: A cantool session.
    '''
    line = session.readline()
    return line

async def writecan(session, data_id, data):
    ''' An 'awaitable' can write wrapper.

    Allows code to continue execution while waiting for write task to return

    Args:
        session: A cantool session
        id: Hex can id
        data: Hex data to transmit
    '''
    session.write(data_id, data)

async def cannit():
    '''Uses the pykarbon module to attach to the karbon can hardware

    Allows for reading/writing to the can port. Displays the last message sent/read.
    It will also save all received messages to a .csv on exit
    '''

    with cantool.Session(timeout=None) as candev:

        read_task = asyncio.create_task(readcan(candev))
        write_task = asyncio.create_task(writecan(candev, 0x11, 0x11223344))

        await write_task
        print("Write complete")

        await read_task
        print("Read complete")

        candev.storedata("can_data")

    return 0

if __name__ == "__main__":
    asyncio.run(cannit())
