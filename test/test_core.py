''' Test pykarbon.core functions '''
import pykarbon.core as pkcore
from time import sleep
import re


def test_command():
    with pkcore.Terminal() as dev:
        out = dev.command('version')[0]

    assert re.match(r'<.*>', out)


def test_command_print(capsys):
    with pkcore.Terminal() as dev:
        dev.print_command('version')

    captured = capsys.readouterr()
    assert re.match(r'<.*>', captured.out)


def test_grepall():
    out = None
    with pkcore.Terminal() as dev:
        dev.write('version')
        out = dev.grepall(r'(\d\.){3}\d', None)

    assert out


def test_dio_controls():
    out = []
    sts = []
    with pkcore.Terminal() as dev:
        dev.write('set-do 0000')

        out.append(dev.get_state(0))
        sts.append(dev.input_states())

        dev.set_high(0)
        sleep(.75)

        out.append(dev.get_state(0))
        sts.append(dev.input_states())

        dev.set_low(0)
        sleep(.75)

        out.append(dev.get_state(0))
        sts.append(dev.input_states())

    assert (sts[0] == sts[2] == ['1', '1', '1', '1'])
    assert (sts[1] == ['0', '1', '1', '1'])
    assert (out[0] == out[2] == '1') and (out[1] == '0')


def test_cleanout():
    with pkcore.Terminal() as dev:
        dev.write('dio-state')
        sleep(.1)
        dev.cleanout()

        out = dev.readall([])[0]

    assert not out


def test_send():
    expected = {'format': 'std', 'id': '123', 'data': 'deadbeef', 'len': '4', 'type': 'data'}
    with pkcore.Can() as dev:
        out = dev.send(0x123, 0xDEADBEEF)
        for i in range(0, 10):
            resp = dev.cread()[0].strip('\r\n')
            if resp:
                break

    assert resp == '123 DEADBEEF'
    assert expected == out
