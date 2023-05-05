# *****************************************************************************
# * | File        :	  Pico_ePaper-2.66-B.py
# * | Author      :   Waveshare team
# * | Function    :   Electronic paper driver
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2021-05-14
# # | Info        :   python demo
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# https://github.com/waveshare/Pico_ePaper_Code/blob/main/python/Pico_ePaper-2.66-B.py

from machine import Pin, SPI
import framebuf
import utime

# Display resolution
EPD_WIDTH = 152
EPD_HEIGHT = 296

RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13

WF_PARTIAL_2IN66 = [
    0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x80, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x40, 0x40, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x22, 0x22, 0x22, 0x22, 0x22, 0x22,
    0x00, 0x00, 0x00, 0x22, 0x17, 0x41, 0xB0, 0x32, 0x36,
]

# Use a byte as the key to retrive it's bits in reversed order.
# ex: byte_lookup[01010101] == 10101010
byte_lookup = [
    0x00, 0x80, 0x40, 0xC0, 0x20, 0xA0, 0x60, 0xE0, 0x10, 0x90, 0x50, 0xD0, 0x30, 0xB0, 0x70, 0xF0,
    0x08, 0x88, 0x48, 0xC8, 0x28, 0xA8, 0x68, 0xE8, 0x18, 0x98, 0x58, 0xD8, 0x38, 0xB8, 0x78, 0xF8,
    0x04, 0x84, 0x44, 0xC4, 0x24, 0xA4, 0x64, 0xE4, 0x14, 0x94, 0x54, 0xD4, 0x34, 0xB4, 0x74, 0xF4,
    0x0C, 0x8C, 0x4C, 0xCC, 0x2C, 0xAC, 0x6C, 0xEC, 0x1C, 0x9C, 0x5C, 0xDC, 0x3C, 0xBC, 0x7C, 0xFC,
    0x02, 0x82, 0x42, 0xC2, 0x22, 0xA2, 0x62, 0xE2, 0x12, 0x92, 0x52, 0xD2, 0x32, 0xB2, 0x72, 0xF2,
    0x0A, 0x8A, 0x4A, 0xCA, 0x2A, 0xAA, 0x6A, 0xEA, 0x1A, 0x9A, 0x5A, 0xDA, 0x3A, 0xBA, 0x7A, 0xFA,
    0x06, 0x86, 0x46, 0xC6, 0x26, 0xA6, 0x66, 0xE6, 0x16, 0x96, 0x56, 0xD6, 0x36, 0xB6, 0x76, 0xF6,
    0x0E, 0x8E, 0x4E, 0xCE, 0x2E, 0xAE, 0x6E, 0xEE, 0x1E, 0x9E, 0x5E, 0xDE, 0x3E, 0xBE, 0x7E, 0xFE,
    0x01, 0x81, 0x41, 0xC1, 0x21, 0xA1, 0x61, 0xE1, 0x11, 0x91, 0x51, 0xD1, 0x31, 0xB1, 0x71, 0xF1,
    0x09, 0x89, 0x49, 0xC9, 0x29, 0xA9, 0x69, 0xE9, 0x19, 0x99, 0x59, 0xD9, 0x39, 0xB9, 0x79, 0xF9,
    0x05, 0x85, 0x45, 0xC5, 0x25, 0xA5, 0x65, 0xE5, 0x15, 0x95, 0x55, 0xD5, 0x35, 0xB5, 0x75, 0xF5,
    0x0D, 0x8D, 0x4D, 0xCD, 0x2D, 0xAD, 0x6D, 0xED, 0x1D, 0x9D, 0x5D, 0xDD, 0x3D, 0xBD, 0x7D, 0xFD,
    0x03, 0x83, 0x43, 0xC3, 0x23, 0xA3, 0x63, 0xE3, 0x13, 0x93, 0x53, 0xD3, 0x33, 0xB3, 0x73, 0xF3,
    0x0B, 0x8B, 0x4B, 0xCB, 0x2B, 0xAB, 0x6B, 0xEB, 0x1B, 0x9B, 0x5B, 0xDB, 0x3B, 0xBB, 0x7B, 0xFB,
    0x07, 0x87, 0x47, 0xC7, 0x27, 0xA7, 0x67, 0xE7, 0x17, 0x97, 0x57, 0xD7, 0x37, 0xB7, 0x77, 0xF7,
    0x0F, 0x8F, 0x4F, 0xCF, 0x2F, 0xAF, 0x6F, 0xEF, 0x1F, 0x9F, 0x5F, 0xDF, 0x3F, 0xBF, 0x7F, 0xFF
]


class EPD_2in9_B:
    def __init__(self):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)

        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.lut = WF_PARTIAL_2IN66

        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

        self.invert_x = False
        self.invert_y = False

        self.buffer_black = bytearray(self.height * self.width // 8)
        self.buffer_red = bytearray(self.height * self.width // 8)
        self.imageblack = framebuf.FrameBuffer(
            self.buffer_black, self.width, self.height, framebuf.MONO_HLSB)
        self.imagered = framebuf.FrameBuffer(
            self.buffer_red, self.width, self.height, framebuf.MONO_HLSB)
        self.init()

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def SetWindow(self, x_start, y_start, x_end, y_end):
        self.send_command(0x44)
        self.send_data((x_start >> 3) & 0x1f)
        self.send_data((x_end >> 3) & 0x1f)

        self.send_command(0x45)
        self.send_data(y_start & 0xff)
        self.send_data((y_start & 0x100) >> 8)
        self.send_data((y_end & 0xff))
        self.send_data((y_end & 0x100) >> 8)

    def SetCursor(self, x_start, y_start):
        self.send_command(0x4E)
        self.send_data(x_start & 0x1f)

        self.send_command(0x4f)
        self.send_data(y_start & 0xff)
        self.send_data((y_start & 0x100) >> 8)

    def ReadBusy(self):
        utime.sleep_ms(50)
        while (self.busy_pin.value() == 1):      # 0: idle, 1: busy
            utime.sleep_ms(10)

        utime.sleep_ms(50)

    def TurnOnDisplay(self):
        self.send_command(0x20)
        self.ReadBusy()

    def init(self):
        self.reset()
        self.ReadBusy()
        self.send_command(0x12)
        self.ReadBusy()  # waiting for the electronic paper IC to release the idle signal

        self.send_command(0x11)
        self.send_data(0x03)

        self.SetWindow(0, 0, self.width-1, self.height-1)

        self.send_command(0x21)  # resolution setting
        self.send_data(0x00)
        self.send_data(0x80)

        self.SetCursor(0, 0)
        self.ReadBusy()

    def display(self, invert_x=None, invert_y=None):
        high = self.height
        if (self.width % 8 == 0):
            wide = self.width // 8
        else:
            wide = self.width // 8 + 1

        ix = invert_x if invert_x is not None else self.invert_x
        iy = invert_y if invert_y is not None else self.invert_y

        def iter_x(value):
            r = range(0, value)
            return r if ix is not True else reversed(r)

        def iter_y(value):
            r = range(0, value)
            return r if iy is not True else reversed(r)

        bl_y = (lambda b: byte_lookup[b]) if iy else (lambda b: b)

        self.send_command(0x24)
        for j in iter_x(high):
            for i in iter_y(wide):
                b = self.buffer_black[i + j * wide]
                b = bl_y(b)
                self.send_data(b)

        self.send_command(0x26)
        for j in iter_x(high):
            for i in iter_y(wide):
                b = ~self.buffer_red[i + j * wide]
                b = bl_y(b)
                self.send_data(b)

        self.TurnOnDisplay()

    def Clear(self, colorblack, colorred):
        high = self.height
        if (self.width % 8 == 0):
            wide = self.width // 8
        else:
            wide = self.width // 8 + 1

        self.send_command(0x24)

        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(colorblack)
        self.send_command(0x26)

        for j in range(0, high):
            for i in range(0, wide):
                self.send_data(~colorred)

        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0X10)  # deep sleep
        self.send_data(0x01)


# if __name__=='__main__':
#     epd = EPD_2in9_B()
#     epd.Clear(0xff, 0xff)

#     epd.imageblack.fill(0xff)
#     epd.imagered.fill(0xff)
#     epd.imageblack.text("Waveshare", 0, 10, 0x00)
#     epd.imagered.text("ePaper-2.66-B", 0, 25, 0x00)
#     epd.imageblack.text("RPi Pico", 0, 40, 0x00)
#     epd.imagered.text("Hello World", 0, 55, 0x00)
#     epd.display()
#     epd.delay_ms(2000)

#     epd.imagered.vline(10, 90, 40, 0x00)
#     epd.imagered.vline(90, 90, 40, 0x00)
#     epd.imageblack.hline(10, 90, 80, 0x00)
#     epd.imageblack.hline(10, 130, 80, 0x00)
#     epd.imagered.line(10, 90, 90, 130, 0x00)
#     epd.imageblack.line(90, 90, 10, 130, 0x00)
#     epd.display()
#     epd.delay_ms(2000)

#     epd.imageblack.rect(10, 150, 40, 40, 0x00)
#     epd.imagered.fill_rect(60, 150, 40, 40, 0x00)
#     epd.display()
#     epd.delay_ms(2000)


#     epd.Clear(0xff, 0xff)
#     epd.delay_ms(2000)
#     print("sleep")
#     epd.sleep()
