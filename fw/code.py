# By Guy Dupont
# Currently running on nRF based CircuitPython boards - will hopefully be compatible with ESP boards soon!

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import Advertisement
from adafruit_ble.services import Service
from adafruit_ble.characteristics import Characteristic
from adafruit_ble.characteristics.string import StringCharacteristic
from adafruit_ble.uuid import VendorUUID
from digitalio import DigitalInOut, Direction, Pull
import _bleio
import pwmio
import board
import time

MAX_AMP_SCALE = 10
amplitude_scale = 5
amplitude_scale_str = str(amplitude_scale)

# Should match the number of LEDs on the baby monitor
MAX_AMP = 5

motor_pin = pwmio.PWMOut(board.D4, frequency=8000, duty_cycle=0)

# Where the baby monitor LEDs are hooked up
input_pin_ids = [board.D5, board.D6, board.D7, board.D8, board.D9]
input_pins = []
for id in input_pin_ids:
    pin = DigitalInOut(id)
    pin.direction = Direction.INPUT
    pin.pull = Pull.UP
    input_pins.append(pin)

# Custom BLE Service with characteristics for setting vibration strength, and transmitting real-time amplitude
class CustomService(Service):
    uuid = VendorUUID("3a40992e-127b-11ed-861d-0242ac120001")
    value = StringCharacteristic(
        uuid=VendorUUID("3a40992e-127b-11ed-861d-0242ac120002"),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
    )
    amplitude_scale = StringCharacteristic(
        uuid=VendorUUID("3a40992e-127b-11ed-861d-0242ac120003"),
        properties=(Characteristic.READ | Characteristic.WRITE),
        initial_value=amplitude_scale_str
    )


adapter = _bleio.adapter
adapter.name = "HACKED Baby Monitor"
service = CustomService()

ble = BLERadio(adapter)
a = Advertisement()
a.connectable = True

def read_amplitude():
    # this is the count of LEDs that are on
    amp_sum = 5
    for pin in input_pins:
        # subtract one for every pin that it is on
        amp_sum -= 1 if pin.value else 0
    # vibration strength
    motor_pin.duty_cycle = int((amplitude_scale / MAX_AMP_SCALE) * ((65535 / MAX_AMP) * amp_sum))
    return amp_sum

def update_amplitude_scale():
    global amplitude_scale, amplitude_scale_str
    # check if amplitude scale has been updated via BLE
    current_amplitude_scale = service.amplitude_scale
    # the characteristic value can either be a string or a byte array
    # it's easier for the user to enter the string representation of the number
    # so just expect an int encoded as a string from "1" to "10"
    if amplitude_scale_str != current_amplitude_scale:
        if current_amplitude_scale.isdigit():
            amplitude_scale = int(current_amplitude_scale)
            if amplitude_scale > MAX_AMP_SCALE:
                amplitude_scale = MAX_AMP_SCALE
            print("set amplitude scale", amplitude_scale)
            amplitude_scale_str = str(amplitude_scale)
        service.amplitude_scale = amplitude_scale_str

# Update amplitude value on BLE characteristic
def update_ble_output(value):
    service.value = str(value)
    
while True:
    ble.start_advertising(a)
    while not ble.connected:
        read_amplitude()
        time.sleep(0.01)
    while ble.connected:
        # only check if this is updated every once in a while, not super urgent
        update_amplitude_scale()
        for _ in range(10):
            time.sleep(0.01)
            update_ble_output(read_amplitude())