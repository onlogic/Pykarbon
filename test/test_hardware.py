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

def test_multiple_release():
    ''' Ensure that is allowed to close a closed port '''
    term = pk.Interface('terminal')
    term.claim()

    term.release()
    term.release()
    term.release()

def test_unclaimed_read_write():
    ''' Check that correct errors are thrown when a user tries a closed port '''
    from pytest import raises
    term = pk.Interface('terminal')

    with raises(ConnectionError):
        term.cwrite('version')

    with raises(ConnectionError):
        term.cread()

def test_multiple_argument_writes():
    ''' Check that buffer is cleared in such a way that multi-argument writes always succeed '''
    test_values = ['700', '710', '720', '730', '740', '750', '800']
    out_values = []
    with pk.Interface('terminal') as term:
        for value in test_values:
            term.cwrite('set can-baudrate {}'.format(value))
            out_values.append(term.cread()[0])

    for value in out_values:
        assert 'Error' not in value
