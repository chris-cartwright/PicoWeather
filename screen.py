import eink
import time
from writer import Writer
from fonts import arial10, arial35, arial50


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


def update_display(weather, limits):
    global epd, black_proxy, red_proxy

    def within_limits(name, value):
        lims = limits[name]
        if value <= lims['low']:
            return False

        if value >= lims['high']:
            return False

        return True

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
    val = round(weather['main']['temp'])
    writer = w50black if within_limits('temp', val) else w50red
    s = str(val)
    center_string(writer, s, line)
    writer.printstring(s)
    line += 55

    # Humidity
    val = weather['main']['humidity']
    writer = w35black if within_limits('humidity', val) else w35red
    s = f"{val}%"
    center_string(writer, s, line)
    writer.printstring(s)
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
        val = round(weather['wind']['gust'])
        writer = w35black if within_limits('gusts', val) else w35red
        s = f"{val}"
        Writer.set_textpos(writer.device, line, colw)
        writer.printstring(s)

    val = round(weather['wind']['speed'])
    writer = w35black if within_limits('wind', val) else w35red
    s = str(val)
    right_string(writer, s, line, dw=subcolw)
    writer.printstring(s)
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
