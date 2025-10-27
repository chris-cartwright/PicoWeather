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
import screen
from screen import show_error, update_display
import micropython
import util

_debug_mode = True

WIFI_SSID = settings.WIFI_SSID
WIFI_PASSWD = settings.WIFI_PASSWD
WEATHER_URL = "https://automate-this.internal.chris-cartwright.com/v1/weather"
LOCALE_URL = "https://automate-this.internal.chris-cartwright.com/v1/locale_info"
MAX_UPDATE_FREQ = 60 * 5  # 5m in seconds

rp2.country("CA")
ntptime.host = settings.NTP_HOST  # Need a localtime NTP host

wlan = None
time_set = None
last_update = None

battery_pin = machine.ADC(28)
charging_pin = Pin("WL_GPIO2", Pin.IN)
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
        "charging": c == 1,
        "reading": reading,
        "low": low,
        "high": high,
        "level": (reading - low) / (high - low),
    }


def set_time(init=False):
    global time_set
    global wlan

    now = time.time()
    if time_set is not None and (now - time_set) < (60 * 24):
        return

    if wlan is not None and wlan.isconnected():
        old_time = time.time()
        ntptime.settime()
        time_set = time.time()

        # Logs showed the time jumped from year 2025 to 2036 for some reason.
        max_change = 6 * 60 * 60  # 6 hours
        if (time_set - old_time > max_change) and not init:
            machine.RTC().datetime(time.gmtime(old_time))
            if _debug_mode:
                print(
                    f"set_time: NTP time too far out of range. Old: {old_time}  NTP: {time_set}. Reset to old time."
                )
        elif _debug_mode:
            print(f"set_time: NTP time set: {time.gmtime()}")

        try:
            response = requests.get(LOCALE_URL, headers={"x-unix-timestamps": "true"})
            if response.status_code != 200:
                return
        except Exception as e:
            print("set_time: Failed to acquire locale data")
            print(e)
            return

        try:
            locale_info = json.loads(response.text)
            util.tz_offset = locale_info["timeZoneOffset"]
        except Exception as e:
            print("set_time: Failed to adjust for timezone")
            print(e)
    else:
        if _debug_mode:
            print("set_time: WiFi disconnected. Time not updated.")


def connect():
    global wlan

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        print("connect: Already connected.")
        set_time()
        return

    wlan.active(True)
    wlan.config(pm=0xA11140)
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
        with open("weather.json", "r") as f:
            old = json.load(f)

        old_time = old["timestamp"]

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
    with open("weather.json", "w") as f:
        json.dump(weather, f)
        f.flush()


def update_weather():
    try:
        response = requests.get(WEATHER_URL, headers={"x-unix-timestamps": "true"})
        if response.status_code != 200:
            return None
    except Exception as e:
        print("update_weather: Failed to acquire weather data")
        print(e)
        return None

    return json.loads(response.text)


def load_limits():
    try:
        with open("limits.json", "r") as f:
            data = json.load(f)

        return data

    except OSError:
        pass
    except ValueError:
        pass

    return {
        "temp": {"low": -15, "high": 25},
        "humidity": {"low": -1, "high": 80},
        "wind": {"low": -1, "high": 10},
        "gusts": {"low": -1, "high": 20},
    }


def save_limits(limits):
    with open("limits.json", "w") as f:
        json.dump(limits, f)
        f.flush()


@util.singleton
def tick(_: Timer):
    print(f"tick: Begin: {time.localtime()}")

    global wlan, last_update

    now = time.time()
    if last_update is not None:
        diff = now - last_update
        if diff < MAX_UPDATE_FREQ:
            print(f"tick: Must wait {MAX_UPDATE_FREQ}s. Last update {diff}s ago.")
            return

    last_update = now

    if battery_stats()["level"] <= 0.1:
        # Skip update if power is low. Screen is sensitive.
        print("tick: Low power; skip screen refresh.")
        return

    print("tick: Battery OK")
    if wlan is None or not wlan.isconnected():
        # WLAN is unstable for some reason. Keep trying.
        counter = 0
        while counter < 10:
            try:
                connect()
                if wlan is not None and wlan.isconnected():
                    break

                if wlan is not None:
                    print("tick: Connect failed, disconnect.")
                    wlan.disconnect()

            except OSError as e:
                if wlan is not None:
                    print("tick: Error, disconnect.")
                    print(e)
                    wlan.disconnect()

            counter += 1

    if wlan is None or not wlan.isconnected():
        print("tick: Error, no network.")
        return

    weather = load_weather()

    if weather is None:
        weather = update_weather()
        if weather is not None:
            save_weather(weather)

    if weather is not None:
        print("tick: Update screen")
        limits = load_limits()
        update_display(weather, limits, battery_stats())
    else:
        print("tick: No data")
        show_error("No data")


@rp2.asm_pio(set_init=rp2.PIO.IN_HIGH)
def debounce():
    label("top")
    wait(0, pin, 0)

    # Meant to be run at 2,000Hz.
    # 2000Hz * 30ms = 2000 * 0.03 = 60 instructions
    set(x, 2)
    label("waiter")
    nop()[29]
    jmp(x_dec, "waiter")
    jmp(pin, "top")
    irq(rel(0))

    # Wait for button to be released
    wait(1, pin, 0)


@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH)
def power_led():
    pull(block)
    mov(y, osr)

    label("counter")

    # Cycles: 1 + 7 + 32 * (30 + 1) = 1000
    set(pins, 0)
    set(x, 31)[6]
    label("delay_low")
    nop()[29]
    jmp(x_dec, "delay_low")

    # Cycles: 1 + 7 + 32 * (30 + 1) = 1000
    set(pins, 1)
    set(x, 31)[6]
    label("delay_high")
    nop()[29]
    jmp(x_dec, "delay_high")

    # Keep flashing LED?
    jmp(y_dec, "counter")


def blink_power_led(count):
    # `jmp(y_dec, 'counter')` uses value prior to decrement
    count -= 1

    # Check if LED is already blinking
    if power_led_sm.tx_fifo() > 0:
        return

    power_led_sm.put(count)


def button_press(_: None):
    if _debug_mode:
        print("Button press!")

    blink_power_led(5)
    update()
    tick(ticker)


def feed(*_):
    global _debug

    if _debug:
        print("Feeding time!")

    wdt()


def main(wdt):
    global ticker, button_sm, power_led_sm

    ticker = Timer()

    button_sm = rp2.StateMachine(
        0, debounce, freq=2000, in_base=button_pin, jmp_pin=button_pin
    )
    button_sm.irq(lambda _: micropython.schedule(button_press, None))
    button_sm.active(1)

    power_led_sm = rp2.StateMachine(1, power_led, freq=2000, set_base=power_led_pin)
    power_led_sm.active(1)

    p = 1000 * 60 * 30  # 30 minutes
    ticker.init(period=p, mode=Timer.PERIODIC, callback=tick)
    tick(ticker)

    wdt_timer = Timer()
    p = 1000 * 15  # 15 seconds

    wdt_timer.init(period=p, mode=Timer.PERIODIC, callback=feed)

    set_time(True)


if __name__ == "__main__":
    print("Running main program...")
    print("Debug: ", _debug_mode)
    # Initialize here before touching main program to ensure setup.
    import watchdog

    watchdog.debug_mode(_debug_mode)

    wdt = watchdog.WatchdogTimer(120)
    print("Watchdog set.")

    screen.debug_mode(_debug_mode)
    main(wdt)
