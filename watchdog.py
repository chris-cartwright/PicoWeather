from machine import WDT, Timer
from micropython import schedule
from time import ticks_ms, ticks_diff

_debug = False

def debug(enabled: bool):
    _debug = enabled


class WatchdogTimer:
    _timer: Timer = None
    _counter: int = 0
    _wdt: WDT = None
    _timeout: int = 0

    def __init__(self, timeout: int):
        self._timeout = timeout
        self._wdt = _FakeWDT()  # WDT(timeout=3000)

        self.feed()
        self._timer = Timer(period=1000, mode=Timer.PERIODIC, callback=self._validate)

    def __call__(self):
        self.feed()

    def feed(self):
        self._counter = self._timeout

    def _print(self, _):
        global _debug

        if _debug:
            print(f"[INTR] Counter: {self._counter}")

    def _validate(self, _):
        schedule(self._print, None)
        self._counter -= 1

        if self._counter > 0:
            self._wdt.feed()


class _FakeWDT:
    def __init__(self, timeout: int = 5000):
        self._timeout = timeout
        self._last = ticks_ms()

    def feed(self):
        schedule(self._feed, None)

    def _feed(self, _):
        global _debug

        elapsed = ticks_diff(ticks_ms(), self._last)
        self._last = ticks_ms()
        if _debug:
            print(f"I have been fed. Elapsed: {elapsed}")
