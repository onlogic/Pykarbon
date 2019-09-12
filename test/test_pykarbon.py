''' Tests covering the integrated pykarbon module '''
from time import sleep, time
import re
import pykarbon.pykarbon as pk

STANDARD_DELAY = .75


def test_close_open():
    ''' Tests that a connection can be opened and closed '''

    dev = pk.Karbon()

    assert dev.can.isopen
    assert dev.terminal.isopen

    dev.close()

    assert not dev.can.isopen
    assert not dev.can.isopen


def test_context_manager():
    ''' Tests that we can use pykarbon as a context managed system '''

    with pk.Karbon() as dev:
        assert dev.can.isopen
        assert dev.terminal.isopen


def test_context_manager_time():
    ''' Test that the context manager can be opened and used in a reasonable timeframe '''
    start = time()
    with pk.Karbon() as dev:
        dev.show_info()
        out = dev.terminal.info['version']['value']

    end = time() - start

    assert end < 15
    assert re.match(r'(v)?(\d\.){3}\d', out)


def test_can_write():
    ''' Test that we can write to the can bus '''

    out = ''
    with pk.Karbon() as dev:
        dev.write(0x123, 0x11223344)
        sleep(STANDARD_DELAY)
        out = dev.can.popdata()

    assert '123 11223344' in out


def test_do_set():
    ''' Test that we can set digital outputs '''
    out = ''
    with pk.Karbon() as dev:
        dev.write(0, '1')
        sleep(STANDARD_DELAY)
        dev.write(0, '0')
        out = dev.terminal.popdata()

    assert out


def test_param_set(capsys):
    ''' Check that we can set configuration parameters '''
    out = ''
    with pk.Karbon(baudrate=None) as dev:
        dev.write('can-baudrate', '750')

        sleep(STANDARD_DELAY)
        out = (dev.terminal.info['can-baudrate']['value'])
        dev.write('can-baudrate', '800')

    captured = capsys.readouterr()

    assert 'Error' not in captured.out
    assert '750' in out


def test_write_generic_string():
    ''' Confirm that we can write a generic string to the port '''
    from re import match

    dev = pk.Karbon(automon=False)
    dev.open()
    dev.write('version')
    sleep(STANDARD_DELAY)
    out = dev.read()

    dev.close()

    check = match(r"<.+v(\d\.){3}\d.+>", out)
    assert check


def test_show_info():
    ''' Test that we can show info '''
    with pk.Karbon() as dev:
        dev.show_info()
