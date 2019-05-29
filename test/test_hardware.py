''' Tests for the basic underlying tools -- discovering ports, etc. '''
import re
import pykarbon.hardware as pk

def test_port_discovery():
    ''' Test that both ports are discovered '''
    found_ports = pk.Hardware().get_ports()

    assert 'can' in found_ports
    assert 'terminal' in found_ports

def test_port_claim_release():
    ''' Confirm that ports can be claimed and released by pyserial '''
    term = pk.Interface('terminal')
    can = pk.Interface('can')

    term.claim()
    can.claim()

    assert term.ser.is_open
    assert can.ser.is_open

    term.release()
    can.release()

    assert not term.ser
    assert not can.ser

def test_read_write():
    ''' Confirm that we can write to both ports '''

    term = pk.Interface('terminal')
    term.claim()

    can = pk.Interface('can')
    can.claim()

    term.cwrite('version')
    can.cwrite('std 123 8 1122334455667788 data')

    term_out = term.cread()
    can_out = can.cread()

    match = re.match(r"<.+v(\d\.){3}\d.+>", term_out[0])
    assert match
    assert '123 1122334455667788' in can_out[0]

def test_context_manager():
    ''' Check that we can use the interface as a context manager '''

    out = ''
    with pk.Interface('terminal') as term:
        term.cwrite('version')
        out = term.cread()

    match = re.match(r"<.+v(\d\.){3}\d.+>", out[0])
    assert match
