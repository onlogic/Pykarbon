''' Test pykarbon.i2c functions '''
import pykarbon.i2c as pki


def test_read():
    device_id = 0x21
    register = 0x99

    print("Trying to read register 0x{:X} from device 0x{:X}".format(register, device_id))

    dev = pki.Device(device_id)

    dev.write(register, 0x78)
    val = dev.read(register)

    assert val == 0x78


def test_write():
    device_id = 0x21
    register = 0x99

    print("Trying to read register 0x{:X} from device 0x{:X}".format(register, device_id))

    dev = pki.Device(device_id)

    val = dev.write(register, 0xFF)
    val2 = dev.write(register, 0x78)

    assert not val
    assert not val2


def test_verified_write():
    device_id = 0x21
    register = 0x99

    dev = pki.Device(device_id)

    val = dev.verified_write(register, 0xFF)
    val2 = dev.verified_write(register, 0x78)

    assert val
    assert val2
