
print("waveshare_esp32_s3_touch_lcd_28.py initialization")
# Hardware initialization for ESP32-S3-Touch-LCD-2.8
# Manufacturer's website at https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-2.8
import lcd_bus
import machine
import i2c

import lvgl as lv
import task_handler

import drivers.display.st7789 as st7789
import drivers.indev.cst328 as cst328

import mpos.ui

# Pin configuration - Display SPI
SPI_BUS = 2
SPI_FREQ = 40000000
LCD_SCLK = 40
LCD_MOSI = 45
LCD_DC = 41
LCD_CS = 42
LCD_RST = 39
LCD_BL = 5

# Touch I2C (bus 0)
I2C_BUS = 0
I2C_FREQ = 400000
TP_SDA = 1
TP_SCL = 3
TP_RST = 2
TP_INT = 4
TP_ADDR = 0x1A
TP_REGBITS = 16

# Sensor I2C (bus 1) - separate from touch
SENSOR_I2C_BUS = 1
SENSOR_SDA = 11
SENSOR_SCL = 10

TFT_HOR_RES=240
TFT_VER_RES=320

try:
    spi_bus = machine.SPI.Bus(
        host=SPI_BUS,
        mosi=LCD_MOSI,
        sck=LCD_SCLK
    )
except TypeError:
    # machine.SPI.Bus fails on soft reboot because the SPI peripheral is
    # already claimed.  Deinit first, then retry.
    machine.SPI(SPI_BUS).deinit()
    spi_bus = machine.SPI.Bus(
        host=SPI_BUS,
        mosi=LCD_MOSI,
        sck=LCD_SCLK
    )

display_bus = lcd_bus.SPIBus(
    spi_bus=spi_bus,
    freq=SPI_FREQ,
    dc=LCD_DC,
    cs=LCD_CS,
)

_BUFFER_SIZE = const(28800)
fb1 = display_bus.allocate_framebuffer(_BUFFER_SIZE, lcd_bus.MEMORY_INTERNAL | lcd_bus.MEMORY_DMA)
fb2 = display_bus.allocate_framebuffer(_BUFFER_SIZE, lcd_bus.MEMORY_INTERNAL | lcd_bus.MEMORY_DMA)

mpos.ui.main_display = st7789.ST7789(
    data_bus=display_bus,
    frame_buffer1=fb1,
    frame_buffer2=fb2,
    display_width=TFT_HOR_RES,
    display_height=TFT_VER_RES,
    color_space=lv.COLOR_FORMAT.RGB565,
    color_byte_order=st7789.BYTE_ORDER_BGR,
    rgb565_byte_swap=False,
    backlight_pin=LCD_BL,
    backlight_on_state=st7789.STATE_HIGH,
    reset_pin=LCD_RST,
    reset_state=st7789.STATE_LOW,
)
mpos.ui.main_display.init()

# Override generic ST7789 init values with Waveshare-specific register settings
# (from official demo Vernon_ST7789T.c - these differ from the generic _st7789_init.py)
mpos.ui.main_display.set_params(0xB0, bytearray([0x00, 0xE8]))        # RAMCTRL
mpos.ui.main_display.set_params(0xB7, bytearray([0x75]))              # Gate Control (generic: 0x35)
mpos.ui.main_display.set_params(0xBB, bytearray([0x1A]))              # VCOM (generic: 0x28)
mpos.ui.main_display.set_params(0xC0, bytearray([0x80]))              # LCM Control (generic: 0x0C)
mpos.ui.main_display.set_params(0xC2, bytearray([0x01, 0xFF]))        # VDV/VRH Enable (generic: 0x01 only)

mpos.ui.main_display.set_power(True)
mpos.ui.main_display.set_backlight(100)

# Touch handling (I2C bus 0):
i2c_bus = i2c.I2C.Bus(host=I2C_BUS, scl=TP_SCL, sda=TP_SDA, freq=I2C_FREQ, use_locks=False)
touch_dev = i2c.I2C.Device(bus=i2c_bus, dev_id=TP_ADDR, reg_bits=TP_REGBITS)
indev = cst328.CST328(touch_dev, reset_pin=TP_RST, startup_rotation=lv.DISPLAY_ROTATION._0)

lv.init()
mpos.ui.main_display.set_rotation(lv.DISPLAY_ROTATION._0)
# Match Waveshare demo: mirror X + BGR (must be after set_rotation which resets MADCTL)
mpos.ui.main_display.set_params(0x36, bytearray([0x48]))

# === SENSOR HARDWARE ===
from mpos import SensorManager

# IMU is on I2C1 (separate bus from touch): SDA=11, SCL=10, addr=0x6B
sensor_i2c_bus = i2c.I2C.Bus(host=SENSOR_I2C_BUS, scl=SENSOR_SCL, sda=SENSOR_SDA, freq=I2C_FREQ, use_locks=False)
SensorManager.init(sensor_i2c_bus, address=0x6B, mounted_position=SensorManager.FACING_EARTH)

print("waveshare_esp32_s3_touch_lcd_28.py finished")
