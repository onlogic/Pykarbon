''' Test pykarbon terminal functionality '''
from time import sleep
import pykarbon.terminal as pkt
STANDARD_DELAY = .75

def test_param_set():
    ''' Tests if parameters can be written to the MCU '''
    defaults = [
        ('ignition-sense', 'off'),
        #('startup-timer', '1'),
        #('shutdown-timer', '10'),
        #('hard-off-timer', '120'),
        ('auto-power-on', 'off'),
        #('shutdown-voltage', '6'),
        ('hotplug', 'on'),
        #('can-baudrate', '800'),
        ('dio-power-switch', 'off'),
        #('boot-config', 'true'),
    ]
    test_values = [
        ('ignition-sense', 'on'),
        #('startup-timer', '2'),
        #('shutdown-timer', '12'),
        #('hard-off-timer', '100'),
        ('auto-power-on', 'on'),
        #('shutdown-voltage', '7'),
        ('hotplug', 'off'),
        #('can-baudrate', '850'),
        ('dio-power-switch', 'off'),
        #('boot-config', 'false')
    ]
    out = ''
    with pkt.Session() as dev:
        for param, value in test_values:
            dev.set_param(param, value, update=False, save_config=False)
            sleep(STANDARD_DELAY)

        sleep(STANDARD_DELAY)
        dev.update_info()
        sleep(STANDARD_DELAY)

        out = dev.info

        for param, value in defaults:
            dev.set_param(param, value, update=False, save_config=False)
            sleep(STANDARD_DELAY)

    for param, value in test_values:
        assert value in out[param]['value']
