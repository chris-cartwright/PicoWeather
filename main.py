import network
import time
import ntptime
import json
import urequests as requests
import rp2
import settings
import machine
import os
from machine import Timer, Pin
from screen import show_error, update_display
import micropython
import util

WIFI_SSID = settings.WIFI_SSID
WIFI_PASSWD = settings.WIFI_PASSWD
DATA_URL = 'https://api.openweathermap.org/data/2.5/weather?q=Winnipeg,Manitoba&units=metric&appid=' + settings.APP_ID
MAX_UPDATE_FREQ = 60 * 5  # 5m in seconds

rp2.country('CA')

wlan = None
time_set = None
last_update = None

battery_pin = machine.ADC(28)
charging_pin = Pin('WL_GPIO2', Pin.IN)
button_pin = Pin(16, Pin.IN, Pin.PULL_UP)
power_led_pin = Pin(17, Pin.OUT)
power_led_pwm = machine.PWM(Pin(18), freq=300_000, duty_u16=20_000)

debug = machine.UART(0, baudrate=9600, rx=Pin(1), tx=Pin(0))
os.dupterm(debug)


def battery_stats():
    low = settings.BATTERY_LOW
    high = settings.BATTERY_HIGH

    c = charging_pin.value()

    # Convert back to original precision, 12bit
    reading = battery_pin.read_u16() >> 4

    return {
        'charging': c == 1,
        'reading': reading,
        'low': low,
        'high': high,
        'level': (reading - low) / (high - low)
    }


def set_time():
    global time_set
    global wlan

    now = time.time()
    if time_set is not None and (now - time_set) < (60 * 24):
        return

    if wlan is not None and wlan.isconnected():
        ntptime.settime()
        time_set = time.time()
        print(f'set_time: NTP time set: {time.localtime()}')


def connect():
    global wlan

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        print("connect: Already connected.")
        set_time()
        return

    wlan.active(True)
    wlan.config(pm=0xa11140)
    wlan.connect(WIFI_SSID, WIFI_PASSWD)

    while not wlan.isconnected() and wlan.status() >= 0:
        machine.idle()

    if wlan.isconnected():
        print("connect: Connected.")
        set_time()
    else:
        print(f"connect: Error: {wlan.status()}")


def load_weather():
    try:
        f = open('weather.json', 'r')
        old = json.load(f)
        f.close()

        old_time = old['dt']

        set_time()
        now = time.time()

        # 25 minutes because it's smaller than the tick interval.
        # Easy way to avoid problems like the 30 minute mark being
        # a second or two into the future.
        if now - old_time < 60 * 25:
            return old

    except OSError:
        pass
    except ValueError:
        pass

    return None


def save_weather(weather):
    f = open('weather.json', 'w')
    json.dump(weather, f)
    f.close()


def update_weather():
    response = requests.get(DATA_URL)
    if response.status_code is not 200:
        return None

    return json.loads(response.text)


def load_limits():
    try:
        f = open('limits.json', 'r')
        data = json.load(f)
        f.close()

        return data

    except OSError:
        pass
    except ValueError:
        pass

    return {
        'temp': {'low': -15, 'high': 25},
        'humidity': {'low': -1, 'high': 80},
        'wind': {'low': -1, 'high': 10},
        'gusts': {'low': -1, 'high': 20}
    }


def save_limits(limits):
    f = open('limits.json', 'w')
    json.dump(limits, f)
    f.close()


@util.singleton
def tick(_: Timer):
    print(f'tick: Begin: {time.localtime()}')

    global wlan, last_update

    now = time.time()
    if last_update is not None:
        diff = now - last_update
        if diff < MAX_UPDATE_FREQ:
            print(
                f'tick: Must wait {MAX_UPDATE_FREQ}s. Last update {diff}s ago.')
            return

    last_update = now

    if battery_stats()['level'] <= 0.1:
        # Skip update if power is low. Screen is sensitive.
        print('tick: Low power; skip screen refresh.')
        return

    print('tick: Battery OK')
    if wlan is None or not wlan.isconnected():
        # WLAN is unstable for some reason. Keep trying.
        counter = 0
        while counter < 10:
            try:
                connect()
                if wlan is not None and wlan.isconnected():
                    break

                if wlan is not None:
                    print('tick: Connect failed, disconnect.')
                    wlan.disconnect()

            except OSError as e:
                if wlan is not None:
                    print('tick: Error, disconnect.')
                    print(e)
                    wlan.disconnect()

            counter += 1

    if wlan is None or not wlan.isconnected():
        print('tick: Error, no network.')
        return

    weather = load_weather()

    if weather is None:
        weather = update_weather()
        if weather is not None:
            save_weather(weather)

    if weather is not None:
        print('tick: Update screen')
        limits = load_limits()
        update_display(weather, limits, battery_stats())
    else:
        print('tick: No data')
        show_error('No data')


@rp2.asm_pio(set_init=rp2.PIO.IN_HIGH)
def debounce():
    label('top')
    wait(0, pin, 0)

    # Meant to be run at 2,000Hz.
    # 2000Hz * 30ms = 2000 * 0.03 = 60 instructions
    set(x, 2)
    label('waiter')
    nop()[29]
    jmp(x_dec, 'waiter')
    jmp(pin, 'top')
    irq(rel(0))

    # Wait for button to be released
    wait(1, pin, 0)


@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH)
def power_led():
    pull(block)
    set(y, osr)
    label('counter')

    # Cycles: 1 + 7 + 32 * (30 + 1) = 1000
    set(pins, 0)
    set(x, 31)[6]
    label('delay_low')
    nop()[29]
    jmp(x_dec, 'delay_low')

    # Cycles: 1 + 7 + 32 * (30 + 1) = 1000
    set(pins, 1)
    set(x, 31)[6]
    label('delay_high')
    nop()[29]
    jmp(x_dec, 'delay_high')

    # Keep flashing LED?
    jmp(y_dec, 'counter')
    set(pins, 1)


def button_press(_: None):
    global ticker, power_led_sm

    print('Button press!')
    power_led_sm.put(5)
    tick(ticker)


ticker = Timer()

button_sm = rp2.StateMachine(0, debounce, freq=2000,
                             in_base=button_pin, jmp_pin=button_pin)
button_sm.irq(lambda _: micropython.schedule(button_press, None))
button_sm.active(1)

power_led_sm = rp2.StateMachine(1, power_led,
                                freq=2000, set_base=power_led_pin)
power_led_sm.active(1)

p = 1000 * 60 * 30  # 30 minutes
ticker.init(period=p, mode=Timer.PERIODIC, callback=tick)
tick(ticker)
