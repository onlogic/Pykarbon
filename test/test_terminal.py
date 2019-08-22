''' Test pykarbon terminal functionality '''
from time import sleep, time
import re

import pykarbon.terminal as pkt

STANDARD_DELAY = .05

def reaction_no_args():
    return ['0', '0', '0', '0']

def reaction_function(dio_state):
    print("Reaction On: " + dio_state)

def wait_re(dev, timeout=1):
    ''' Wait until data has been logged, and then return that data '''
    start = time()
    elapsed = 0
    
    out = ''
    while not out and elapsed < timeout:
        out = dev.popdata()
        elapsed = time() - start

    return out

def reset_do(dev):
    dev.write('set-do 0000')
    wait_re(dev)

    return '0000'

def test_set_do():
    ''' Check the set_do() method '''
    with pkt.Session() as dev:
        temp = reset_do(dev)
        
        for i in range(0, 4):
            dev.set_do(i, True)
            out = wait_re(dev)

            dev.set_do(i, False)
            wait_re(dev)
            
            assert (temp[0:i] + '1' + temp[i + 1:]) == out[-4:]

def test_param_set():
    ''' Tests if parameters can be written to the MCU '''
    defaults = [
        ('ignition-sense', 'off'),
        ('startup-timer', '1'),
        ('shutdown-timer', '10'),
        ('hard-off-timer', '120'),
        ('auto-power-on', 'off'),
        ('shutdown-voltage', '6'),
        ('hotplug', 'on'),
        ('can-baudrate', '800'),
        ('dio-power-switch', 'off'),
        #('boot-config', 'true'),
    ]
    test_values = [
        ('ignition-sense', 'on'),
        ('startup-timer', '2'),
        ('shutdown-timer', '12'),
        ('hard-off-timer', '100'),
        ('auto-power-on', 'on'),
        ('shutdown-voltage', '7'),
        ('hotplug', 'off'),
        ('can-baudrate', '850'),
        ('dio-power-switch', 'off'),
        #('boot-config', 'false')
    ]
    out = ''
    with pkt.Session() as dev:
        for param, value in test_values:
            dev.set_param(param, value, update=False, save_config=False)
            sleep(STANDARD_DELAY)

        sleep(STANDARD_DELAY)
        dev.update_info(print_info=True)
        sleep(STANDARD_DELAY)

        out = dev.info

        for param, value in defaults:
            dev.set_param(param, value, update=False, save_config=False)
            sleep(STANDARD_DELAY)

    for param, value in test_values:
        assert value in out[param]['value']

def test_reactions(capsys):
    with pkt.Session() as dev:
        dev.register(0, 'low', reaction_no_args)

        assert dev.registry[0]

        dev.set_do(0, True)
        assert wait_re(dev) == '0111 1000'
        assert wait_re(dev, timeout=5) == '1111 0000'

        sleep(1)
        dev.register(1, 'high', reaction_function)
        dev.set_do(1, True)
        sleep(STANDARD_DELAY)
        dev.set_do(1, False)
        sleep(1)

    captured = capsys.readouterr()

    assert not captured.err
    assert re.match(r'Reaction On: [0-1]{4} [0-1]{4}', captured.out, re.MULTILINE)
