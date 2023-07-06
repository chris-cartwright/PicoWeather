import network
import time
import ntptime
import json
import urequests as requests
import rp2
import settings
from machine import Timer
from machine import Pin
from screen import show_error, update_display

WIFI_SSID = settings.WIFI_SSID
WIFI_PASSWD = settings.WIFI_PASSWD
DATA_URL = 'https://api.openweathermap.org/data/2.5/weather?q=Winnipeg,Manitoba&units=metric&appid=' + settings.APP_ID

rp2.country('CA')


pin_sensor = Pin(19, Pin.IN)
pin_button = Pin(28, Pin.OUT)

wlan = None
time_set = False


def set_time():
    global time_set
    global wlan

    if time_set is True:
        return

    if wlan is not None and wlan.isconnected():
        ntptime.settime()
        time_set = True


def connect():
    global wlan

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        print("Already connected.")
        set_time()
        return

    wlan.active(True)
    wlan.config(pm=0xa11140)
    wlan.connect(WIFI_SSID, WIFI_PASSWD)

    while not wlan.isconnected() and wlan.status() >= 0:
        print("Waiting to connect:")
        time.sleep(1)

    if wlan.isconnected():
        print("Connected.")
        set_time()
    else:
        print(f"Error: {wlan.status()}")


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


def tick(_: Timer):
    global wlan

    if wlan is None or not wlan.isconnected():
        # WLAN is unstable for some reason. Keep trying.
        counter = 0
        while counter < 10:
            try:
                connect()
                if wlan is not None and wlan.isconnected():
                    break

                if wlan is not None:
                    print('Connect failed, disconnect.')
                    wlan.disconnect()

            except OSError as e:
                if wlan is not None:
                    print('Error, disconnect.')
                    print(e)
                    wlan.disconnect()

            counter += 1

    if wlan is None or not wlan.isconnected():
        show_error('No network')
        return

    weather = load_weather()

    if weather is None:
        weather = update_weather()
        if weather is not None:
            save_weather(weather)

    if weather is not None:
        limits = load_limits()
        update_display(weather, limits)
    else:
        show_error('No data')


ticker = Timer()
p = 1000 * 60 * 30  # 30 minutes
ticker.init(period=p, mode=Timer.PERIODIC, callback=tick)
tick(ticker)
