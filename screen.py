import eink
import time
import gc
import util
from writer import Writer
from fonts import arial10, arial35, arial50

_debug = False

def debug(enabled: bool):
    _debug = enabled


class DebugWriter(Writer):
    @staticmethod
    def set_textpos(device, row=None, col=None):
        global _debug

        if _debug:
            print("set_textpos", (device, row, col))

        Writer.set_textpos(device, row, col)

    @staticmethod
    def get_textpos(device):
        return Writer.get_textpos(device)

    def __init__(self, *args, **kwargs):
        self.writer = Writer(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.writer, attr)

    def printstring(self, string, invert=True):
        global _debug

        if _debug:
            print("printstring: ", (string, invert))

        self.writer.printstring(string, invert)


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


def degrees_to_compass(deg):
    sectors = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
        "N",
    ]
    return sectors[int(round((deg % 360) / 22.5, 0))]


def center_string(font, s, x, dw=None, o=None):
    if dw is None:
        dw = font.device.width

    dw = int(dw)
    w = font.stringlen(s)
    c = (dw / 2) - (w / 2)
    c += o or 0
    c = int(round(c, 0))
    DebugWriter.set_textpos(font.device, x, c)
    return (w, c)


def right_string(font, s, x, dw=None, o=None):
    if dw is None:
        dw = font.device.width

    dw = int(dw)
    w = font.stringlen(s)
    r = dw - w
    r += o or 0
    r = int(round(r, 0))
    DebugWriter.set_textpos(font.device, x, r)
    return (w, r)


# Totaly arbitrary values to put something on the screen.
# Some values are set to multiples of "8" to aid in positioning.
def debug_update_display(gusts=88.88):
    weather = {
        "pressure": 1015,
        "snow": None,
        "sunrise": 1760013668,
        "sunset": 1760053805,
        "cloudCoverage": 0,
        "conditions": [{"main": "Clouds", "description": "few clouds"}],
        "temperature": {
            "current": -88.88,
            "max": -88.88,
            "min": -88.88,
            "feelsLike": -88.88,
        },
        "humidity": 55,
        "wind": {"degrees": 300, "speed": 88.88, "gusts": gusts},
        "rain": None,
        "visibility": 10000,
        "timestamp": 1760047371,
    }
    limits = {
        "temp": {"low": -15, "high": 25},
        "humidity": {"low": -1, "high": 80},
        "wind": {"low": -1, "high": 10},
        "gusts": {"low": -1, "high": 20},
    }

    battery_stats = {
        "charging": True,
        "high": 2180,
        "level": 1.892308,
        "reading": 2644,
        "low": 1660,
    }

    update_display(weather, limits, battery_stats)


def update_display(weather, limits, battery_stats):
    global epd, black_proxy, red_proxy

    gc.collect()

    def within_limits(name, value):
        lims = limits[name]
        if value <= lims["low"]:
            return False

        if value >= lims["high"]:
            return False

        return True

    epd.imageblack.fill(0xFF)
    epd.imagered.fill(0xFF)

    w50black: Writer = DebugWriter(black_proxy, arial50)
    w50red: Writer = DebugWriter(red_proxy, arial50)
    w35black: Writer = DebugWriter(black_proxy, arial35)
    w35red: Writer = DebugWriter(red_proxy, arial35)
    w10black: Writer = DebugWriter(black_proxy, arial10)
    w10red: Writer = DebugWriter(red_proxy, arial10)

    line = 10

    # Current temperature and Feels like
    val = round(weather["temperature"]["current"])
    writer = w50black if within_limits("temp", val) else w50red
    s = str(val)
    DebugWriter.set_textpos(writer.device, line, 3)
    writer.printstring(s)

    s = "Feels like"
    right_string(w10black, s, line)
    w10black.printstring(s)

    val = round(weather["temperature"]["feelsLike"])
    writer = w35black if within_limits("temp", val) else w35red
    s = str(val)
    right_string(writer, s, line + 15)
    writer.printstring(s)

    line += 60

    # Humidity
    val = weather["humidity"]
    writer = w35black if within_limits("humidity", val) else w35red
    s = f"{val}%"
    center_string(writer, s, line)
    writer.printstring(s)
    line += 35

    # High and Low
    s = str(round(weather["temperature"]["max"]))
    (w, l) = center_string(w35black, s, line, dw=black_proxy.width * 0.4)
    w35black.printstring(s)
    s = "Hi"
    DebugWriter.set_textpos(black_proxy, line + 5, l + w + 3)
    w10black.printstring(s)
    s = str(round(weather["temperature"]["min"]))
    (w, l) = center_string(
        w35black, s, line, dw=black_proxy.width * 0.4, o=black_proxy.width * 0.6
    )
    w35black.printstring(s)
    s = "Lo"
    right_string(w10black, s, line + 15, dw=l, o=-3)
    w10black.printstring(s)
    line += 40

    # Wind speed + direction
    val = round(weather["wind"]["speed"])
    writer = w35black if within_limits("wind", val) else w35red
    s = str(round(weather["wind"]["speed"]))
    center_string(writer, s, line, dw=black_proxy.width / 3)
    writer.printstring(s)

    if "gusts" in weather["wind"]:
        val = round(weather["wind"]["gusts"])
        writer = w35black if within_limits("gusts", val) else w35red
        s = str(val)
        center_string(writer, s, line, dw=black_proxy.width / 3, o=black_proxy.width * 0.66)
        writer.printstring(s)

    s = "gust >"
    center_string(w10black, s, line + 2)
    w10black.printstring(s)
    s = degrees_to_compass(weather["wind"]["degrees"])
    center_string(w10black, s, line + 17)
    w10black.printstring(s)
    line += 40

    # Sunrise and sunset
    (_, _, _, hour, minute, *_) = util.localtime(weather["sunrise"])
    s = f"Sunrise: {hour}:{minute}"
    center_string(w10black, s, line, dw=black_proxy.width / 2)
    w10black.printstring(s)

    (_, _, _, hour, minute, *_) = util.localtime(weather["sunset"])
    s = f"Sunset: {hour}:{minute}"
    center_string(w10black, s, line + 12, dw=black_proxy.width / 2)
    w10black.printstring(s)

    # Pressure
    s = f"{weather['pressure']} hPa"
    center_string(w10black, s, line, dw=black_proxy.width / 2, o=black_proxy.width / 2)
    w10black.printstring(s)
    line += 30

    # Overcast?
    s = ", ".join([entry["description"] for entry in weather["conditions"]])
    DebugWriter.set_textpos(black_proxy, line, 0)
    w35black.printstring(s)

    # Last update time, voltage; pinned at bottom
    line = black_proxy.height - 10
    (year, month, day, hour, minute, second, *_) = util.localtime(weather["timestamp"])
    s = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    center_string(w10black, s, line)
    w10black.printstring(s)

    if not battery_stats["charging"]:
        p = battery_stats["level"] * 100
        s = f"{p:.0f}%"
        right_string(w10black, s, line)
        w10black.printstring(s)

    epd.reset()
    epd.Clear(0xFF, 0xFF)
    epd.display()
    epd.sleep()

    gc.collect()


def show_error(msg=None):
    global time_set
    global epd

    print(f"ERROR: {msg}")

    epd.imageblack.fill(0xFF)
    epd.imagered.fill(0xFF)
    epd.imagered.text("Error :(", 0, 10, 0x00)
    epd.imagered.text("Faild to load", 0, 25, 0x00)

    try:
        now = time.gmtime()
        epd.imageblack.text(f"{now[0]}-{now[1]}-{now[2]}", 0, 40, 0x00)
        epd.imageblack.text(f"{now[3]}:{now[4]}:{now[5]}", 0, 55, 0x00)
    except:
        pass

    if msg is not None:
        epd.imagered.text(msg, 0, 70, 0x00)

    epd.reset()
    epd.Clear(0xFF, 0xFF)
    epd.display()
    epd.sleep()
