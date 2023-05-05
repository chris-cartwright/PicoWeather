import network
import time
import eink
import ntptime
import json
import urequests as requests
import rp2
import settings
from machine import Timer

WIFI_SSID = settings.WIFI_SSID
WIFI_PASSWD = settings.WIFI_PASSWD
DATA_URL = 'https://api.openweathermap.org/data/2.5/weather?q=Winnipeg,Manitoba&units=metric&appid=' + settings.APP_ID

rp2.country('CA')

epd = eink.EPD_2in9_B()
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


def update_display(weather):
    global epd

    epd.Clear(0xff, 0xff)

    epd.imageblack.fill(0xff)
    epd.imagered.fill(0xff)
    current = f"Current: {round(weather['main']['temp'])}"
    print(current)
    epd.imageblack.text(current, 0, 10, 0x00)
    feels_like = f"Feels like: {round(weather['main']['feels_like'])}"
    print(feels_like)
    epd.imageblack.text(feels_like, 0, 25, 0x00)
    humidity = f"Humidity: {weather['main']['humidity']}%"
    print(humidity)
    epd.imageblack.text(humidity, 0, 40, 0x00)
    epd.imageblack.text(
       f"Wind: {weather['wind']['speed']}km/h @ {weather['wind']['deg']}deg", 0, 55)
    sunset = time.localtime(weather['sys']['sunset'])
    epd.imageblack.text(f"Sunset: {sunset[3] - 12}:{sunset[4]}", 0, 70, 0x00)
    epd.display()


def show_error(msg=None):
    global time_set
    global epd

    print(f'ERROR: {msg}')

    epd.reset()
    epd.Clear(0xff, 0xff)

    epd.imageblack.fill(0xff)
    epd.imagered.fill(0xff)
    epd.imagered.text("Error :(", 0, 10, 0x00)
    epd.imagered.text("Faild to load", 0, 25, 0x00)

    try:
        now = time.localtime()
        epd.imageblack.text(f"{now[0]}-{now[1]}-{now[2]}", 0, 40, 0x00)
        epd.imageblack.text(f"{now[3]}:{now[4]}:{now[5]}", 0, 55, 0x00)
    except:
        pass

    if msg is not None:
        epd.imagered.text(msg, 0, 70, 0x00)

    epd.display()
    epd.sleep()


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
        update_display(weather)
    else:
        show_error('No data')


def demo():
    epd = eink.EPD_2in9_B()
    epd.Clear(0xff, 0xff)

    epd.imageblack.fill(0xff)
    epd.imagered.fill(0xff)
    epd.imageblack.text("Waveshare", 0, 10, 0x00)
    epd.imagered.text("ePaper-2.66-B", 0, 25, 0x00)
    epd.imageblack.text("RPi Pico", 0, 40, 0x00)
    epd.imagered.text("Hello World", 0, 55, 0x00)
    epd.display()
    epd.delay_ms(2000)

    epd.imagered.vline(10, 90, 40, 0x00)
    epd.imagered.vline(90, 90, 40, 0x00)
    epd.imageblack.hline(10, 90, 80, 0x00)
    epd.imageblack.hline(10, 130, 80, 0x00)
    epd.imagered.line(10, 90, 90, 130, 0x00)
    epd.imageblack.line(90, 90, 10, 130, 0x00)
    epd.display()
    epd.delay_ms(2000)

    epd.imageblack.rect(10, 150, 40, 40, 0x00)
    epd.imagered.fill_rect(60, 150, 40, 40, 0x00)
    epd.display()
    epd.delay_ms(2000)


    epd.Clear(0xff, 0xff)
    epd.delay_ms(2000)
    print("sleep")
    epd.sleep()


ticker = Timer()
p = 1000 * 60 * 30  # 30 minutes
ticker.init(period=p, mode=Timer.PERIODIC, callback=tick)
tick(ticker)
#demo()