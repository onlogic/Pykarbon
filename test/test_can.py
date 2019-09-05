''' Testing the can tools. Assumes the Karbon has all can messages echoed '''
from time import sleep
import pykarbon.can as pkc
import re

STANDARD_DELAY = .75

# --------------------------------------------------------------------------------------
ACTION_ID = 0
ACTION_DATA = 0


def action_with_args(hex_id, hex_data):
    ''' Action called by CAN registry service where data is passed '''
    global ACTION_ID
    global ACTION_DATA

    ACTION_ID = hex_id
    ACTION_DATA = hex_data


def action_no_args():
    ''' Action called by CAN registry service where no data is passed '''
    return {'id': 0x111, 'data': 0x22}

# -------------------------------------------------------------------------------------


def test_open_close():
    ''' Check the port can be opened and closed '''
    dev = pkc.Session(baudrate=800, automon=False)

    assert not dev.isopen

    dev.open()

    assert dev.isopen

    dev.close()

    assert not dev.isopen


def test_push_pop():
    ''' Confirm that data is pushed and popped from queue correctly '''
    dev = pkc.Session(baudrate=800, automon=False)

    assert not dev.data

    dev.pushdata('12 112233')
    assert len(dev.data) == 1
    assert '12 112233' in dev.data[-1]

    dev.pushdata('34 445566')
    assert len(dev.data) == 2
    assert '34 445566' in dev.data[-1]

    out = dev.popdata()
    assert len(dev.data) == 1
    assert '12 112233' in out

    out = dev.popdata()
    assert not dev.data
    assert '34 445566' in out


def test_automon_start_stop():
    ''' Check that automatic port monitoring will be correctly started and stopped '''
    dev = pkc.Session(baudrate=800)

    assert dev.isopen
    assert dev.bgmon.isAlive()

    dev.close()

    assert not dev.isopen
    assert not dev.bgmon.isAlive()


def test_automon_restart():
    ''' Check that automonitoring can be stopped and restarted '''

    dev = pkc.Session(baudrate=800)

    dev.close()

    dev.open()
    dev.bgmonitor()

    assert dev.isopen
    assert dev.bgmon.isAlive()

    dev.close()


def test_autobaud():
    ''' Check that autobaudrate correctly discovers the bus baudrate '''

    dev = pkc.Session()
    sleep(4)

    dev.close()

    assert re.match(r'[\d]+', dev.baudrate)


def test_format_message():
    ''' Check that messages can be formatted into a dictionary correctly '''

    dev = pkc.Session(baudrate=800, automon=False)

    message = dev.format_message(0x123, 0x11223344)
    expected = {'format': 'std', 'id': '123', 'length': 4, 'data': '11223344', 'type': 'data'}

    assert message == expected

    message = dev.format_message(0x800, 0x1122334455)
    expected = {'format': 'ext', 'id': '800', 'length': 5, 'data': '1122334455', 'type': 'data'}

    assert message == expected

    message = dev.format_message(0x123, None)
    expected = {'format': 'std', 'id': '123', 'length': 0, 'data': '', 'type': 'remote'}

    assert message == expected

    message = dev.format_message(0x123, '0x00C2')
    expected = {'format': 'std', 'id': '123', 'length': 2, 'data': '00C2', 'type': 'data'}

    assert message == expected

    message = dev.format_message('999', '00C200C2')
    expected = {'format': 'ext', 'id': '999', 'length': 4, 'data': '00C200C2', 'type': 'data'}

    assert message == expected


def test_read_write():
    ''' Check that can is able to read and write '''
    dev = pkc.Session(baudrate=800, automon=False)
    message = {'format': 'std', 'id': '123', 'length': 4, 'data': '11223344', 'type': 'data'}

    dev.open()

    sent = dev.send_can(message)
    assert 'std 123 4 11223344 data' in sent

    for i in range(0, 50):
        out = dev.readline()
        if out:
            break

    dev.close()
    assert '123 11223344' in out


def test_auto_read_write():
    ''' Confirm that reading and writing still works when automonitoring '''
    dev = pkc.Session(baudrate=800)
    dev.write(0x123, 0x1122334455667788)
    sleep(STANDARD_DELAY)
    dev.write(0x7FF, '0x00C2')
    sleep(STANDARD_DELAY)
    dev.write('999', '00000000DEADBEEF')
    sleep(STANDARD_DELAY)

    dev.close()

    assert '123 1122334455667788' in dev.data
    assert '7FF 00C2' in dev.data
    assert '00000999 00000000DEADBEEF'


def test_storedata():
    ''' Test that we are able to save our data to a csv '''
    from os import remove
    dev = pkc.Session(baudrate=800, automon=False)

    line_one = '123 112233'
    line_two = '456 445566'
    dev.pushdata(line_one)
    dev.pushdata(line_two)

    dev.storedata('test', mode='w+')

    out = []
    with open('test.csv', 'r') as testfile:
        out = testfile.read().split()

    assert line_one.replace(' ', ',') in out[0]
    assert line_two.replace(' ', ',') in out[1]

    remove('test.csv')


def test_context_manager():
    ''' Test that we can use can session in a context manager '''

    with pkc.Session() as dev:
        assert dev.isopen
        assert dev.bgmon.isAlive()

        dev.write(0x123, 0x11223344)
        sleep(STANDARD_DELAY)

        out = dev.popdata()
        assert '123 11223344' in out


def test_can_register():
    ''' Test that we can register and perform actions '''

    dev = pkc.Session(baudrate=800, automon=True)

    dev.register(0x777, action_with_args)
    dev.register(0x666, action_no_args)

    assert dev.registry[0x777].data_id == 0x777
    assert dev.registry[0x666].data_id == 0x666

    dev.pre_data.append('777 11223344')
    dev.pre_data.append('666 11223344')
    sleep(STANDARD_DELAY)

    assert ACTION_ID == 0x777
    assert ACTION_DATA == 0x11223344
    assert '111 22' in dev.data

    dev.send_can(dev.format_message(0x777, 0xFF, length=0))
    sleep(STANDARD_DELAY)

    assert ACTION_ID == 0x777
    assert ACTION_DATA is None

    dev.close()
