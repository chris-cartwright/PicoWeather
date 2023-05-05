import network
import time
import eink
import ntptime
import json
import urequests as requests
import rp2
import settings
from machine import Timer
from writer import Writer
from fonts import arial10, arial35, arial50

WIFI_SSID = settings.WIFI_SSID
WIFI_PASSWD = settings.WIFI_PASSWD
DATA_URL = 'https://api.openweathermap.org/data/2.5/weather?q=Winnipeg,Manitoba&units=metric&appid=' + settings.APP_ID

rp2.country('CA')


class ProxyDevice:
    def __init__(self, device):
        self.device = device
        self.height = 296
        self.width = 152

    def __getattr__(self, attr):
        return getattr(self.device, attr)


epd = eink.EPD_2in9_B()
epd.invert_x = True
epd.invert_y = True
black_proxy = ProxyDevice(epd.imageblack)
red_proxy = ProxyDevice(epd.imagered)
wlan = None
time_set = False


def degrees_to_compass(deg):
    sectors = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
               "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    return sectors[int(round((deg % 360) / 22.5, 0))]


def center_string(font, s, x, dw=None):
    if dw is None:
        dw = font.device.width

    dw = int(dw)
    w = font.stringlen(s)
    c = (dw / 2) - (w / 2)
    c = int(round(c, 0))
    Writer.set_textpos(font.device, x, c)


def right_string(font, s, x, dw=None):
    if dw is None:
        dw = font.device.width

    dw = int(dw)
    w = font.stringlen(s)
    l = dw - w
    l = int(round(l, 0))
    Writer.set_textpos(font.device, x, l)


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
    global epd, black_proxy, red_proxy

    epd.imageblack.fill(0xff)
    epd.imagered.fill(0xff)

    w50black = Writer(black_proxy, arial50)
    w50red = Writer(red_proxy, arial50)
    w35black = Writer(black_proxy, arial35)
    w35red = Writer(red_proxy, arial35)
    w10black = Writer(black_proxy, arial10)
    w10red = Writer(red_proxy, arial10)

    line = 10

    # Current temperature
    s = str(round(weather['main']['temp']))
    center_string(w50black, s, line)
    w50black.printstring(s)
    line += 55

    # Humidity
    s = f"{weather['main']['humidity']}%"
    center_string(w35black, s, line)
    w35black.printstring(s)
    line += 40

    # Feels like
    s = 'Feels like'
    right_string(w10black, s, line + 10, black_proxy.width / 2 - 10)
    w10black.printstring(s)
    Writer.set_textpos(black_proxy, line, round(black_proxy.width / 2))
    w35black.printstring(str(round(weather['main']['feels_like'])))
    line += 40

    # Wind speed + direction
    colw = black_proxy.width
    subcolw = round(colw / 2)
    if 'gust' in weather['wind']:
        colw = round(black_proxy.width * 0.6)
        subcolw = round(colw * 0.66)
        s = f"{round(weather['wind']['gust'])}"
        Writer.set_textpos(black_proxy, line, colw)
        w35black.printstring(s)

    s = str(round(weather['wind']['speed']))
    right_string(w35black, s, line, dw=subcolw)
    w35black.printstring(s)
    Writer.set_textpos(black_proxy, line, subcolw + 5)
    w10black.printstring('km/h')
    Writer.set_textpos(black_proxy, line + 15, subcolw + 5)
    w10black.printstring(degrees_to_compass(weather['wind']['deg']))
    line += 40

    # Sunrise and sunset
    ss = time.gmtime(weather['sys']['sunset'])
    s = f"Sunset {ss[3] + 6}:{ss[4]}"  # lazy timezone conversion
    center_string(w10black, s, line)
    w10black.printstring(s)
    line += 15

    # Overcast?
    s = ', '.join([entry['description'] for entry in weather['weather']])
    # Use up a little extra space at the bottom
    Writer.set_textpos(black_proxy, line + 10, 0)
    w35black.printstring(s)

    epd.reset()
    epd.Clear(0xff, 0xff)
    epd.display()
    epd.sleep()


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


ticker = Timer()
p = 1000 * 60 * 30  # 30 minutes
ticker.init(period=p, mode=Timer.PERIODIC, callback=tick)
tick(ticker)
