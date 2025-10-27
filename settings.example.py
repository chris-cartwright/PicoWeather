import random


def random_string(l=5):
    a = "abcdefghijklmnopqrstuvwxyz0123456789"
    ret = ""
    shift = 32 - (len(a) - 32)  # Full range; probably bias.

    for _ in range(l):
        r = random.getrandbits(6)
        if r >= 32:
            r -= shift

        ret += a[r]

    return ret


WIFI_SSID = ""
WIFI_PASSWD = ""

NTP_HOST = "pool.ntp.org"

BATTERY_LOW = 1660  # 3.4v; Calibrated using benchtop supply
BATTERY_HIGH = 2180  # 4.2v; Calibrated using benchtop supply

MQTT_CLIENT_ID = "pico-weather-" + random_string(5)
MQTT_USER = "pico-weather"
MQTT_PASSWD = ""
MQTT_HOST = ""
