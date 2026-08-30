"""Raspberry Pi 4B drivers. Imported only when --dry-run is off."""

from __future__ import annotations

import time
from typing import Optional

import config
from stroke_sim import Telemetry

def _use_pigpio_factory() -> None:
    """gpiozero on Debian Trixie defaults to lgpio, which rejects 20 kHz PWM."""
    from gpiozero import Device
    from gpiozero.pins.pigpio import PiGPIOFactory

    if type(Device.pin_factory).__name__ == "PiGPIOFactory":
        return
    Device.pin_factory = PiGPIOFactory()


# Gray-code 4× quadrature. Invalid transitions (bit jumps) are ignored.
_QUAD = {
    0b0001: 1,
    0b0111: 1,
    0b1110: 1,
    0b1000: 1,
    0b0010: -1,
    0b1011: -1,
    0b1101: -1,
    0b0100: -1,
}


class PiMotor:
    def __init__(self) -> None:
        from gpiozero import DigitalOutputDevice, PWMOutputDevice

        _use_pigpio_factory()
        self._rpwm = PWMOutputDevice(config.MOTOR_RPWM, frequency=config.MOTOR_PWM_HZ)
        self._lpwm = PWMOutputDevice(config.MOTOR_LPWM, frequency=config.MOTOR_PWM_HZ)
        self._ren = DigitalOutputDevice(config.MOTOR_R_EN)
        self._len = DigitalOutputDevice(config.MOTOR_L_EN)
        self._ren.on()
        self._len.on()
        self.duty = 0.0

    def set_duty(self, duty: float) -> None:
        duty = max(-config.MOTOR_MAX_DUTY, min(config.MOTOR_MAX_DUTY, duty))
        self.duty = duty
        applied = -duty if config.MOTOR_INVERT else duty
        if applied > 0:
            self._lpwm.value = 0
            self._rpwm.value = applied
        elif applied < 0:
            self._rpwm.value = 0
            self._lpwm.value = -applied
        else:
            self._rpwm.value = 0
            self._lpwm.value = 0

    def brake(self) -> None:
        self.duty = 0.0
        self._rpwm.value = 1
        self._lpwm.value = 1

    def stop(self) -> None:
        self.set_duty(0.0)

    def close(self) -> None:
        self.stop()
        self._ren.off()
        self._len.off()
        self._rpwm.close()
        self._lpwm.close()
        self._ren.close()
        self._len.close()


class PiEncoder:
    """Quadrature decoder via pigpio callbacks (handles 600 PPR at speed)."""

    def __init__(self) -> None:
        import pigpio

        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError("pigpio daemon is not running. On the Pi: sudo pigpiod")
        pud = pigpio.PUD_UP if config.ENCODER_PULL_UP else pigpio.PUD_OFF
        for pin in (config.ENCODER_PIN_A, config.ENCODER_PIN_B):
            self._pi.set_mode(pin, pigpio.INPUT)
            self._pi.set_pull_up_down(pin, pud)
        self._position = 0
        self._last_count = 0
        self._last_time = time.monotonic()
        self._rpm = 0.0
        self._prev = (self._pi.read(config.ENCODER_PIN_A) << 1) | self._pi.read(
            config.ENCODER_PIN_B
        )
        self._cb_a = self._pi.callback(config.ENCODER_PIN_A, pigpio.EITHER_EDGE, self._pulse)
        self._cb_b = self._pi.callback(config.ENCODER_PIN_B, pigpio.EITHER_EDGE, self._pulse)

    def _pulse(self, gpio: int, level: int, _tick: int) -> None:
        if level not in (0, 1):
            return
        if gpio == config.ENCODER_PIN_A:
            now = (level << 1) | (self._prev & 1)
        else:
            now = (self._prev & 0b10) | level
        delta = _QUAD.get((self._prev << 2) | now, 0)
        self._position += delta
        self._prev = now

    @property
    def position(self) -> int:
        return self._position

    def rpm(self) -> float:
        now = time.monotonic()
        dt = now - self._last_time
        if dt >= 0.05:
            delta = self._position - self._last_count
            self._rpm = (delta / config.COUNTS_PER_REV) / dt * 60.0
            self._last_count = self._position
            self._last_time = now
        return self._rpm

    def set_home(self) -> None:
        self._position = 0
        self._last_count = 0

    def close(self) -> None:
        self._cb_a.cancel()
        self._cb_b.cancel()
        self._pi.stop()


class PiDisplay:
    def __init__(self) -> None:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import ImageFont

        serial = i2c(port=1, address=config.OLED_I2C_ADDR)
        self._device = ssd1306(serial, width=config.OLED_WIDTH, height=config.OLED_HEIGHT)
        self._font = ImageFont.load_default()

    def render(self, telemetry: Telemetry) -> None:
        from luma.core.render import canvas

        # Top 16 px are yellow on the UCTRONICS yellow/blue module.
        with canvas(self._device) as draw:
            header = f"{telemetry.state}  {telemetry.angle_deg:5.1f}d"
            draw.text((0, 0), header[:21], font=self._font, fill=255)
            draw.text(
                (0, 16),
                f"TGT {telemetry.target:5.1f}{telemetry.target_name[0].upper()}",
                font=self._font,
                fill=255,
            )
            draw.text((0, 28), f"DUTY {telemetry.duty*100:5.1f}%", font=self._font, fill=255)
            hit = "--" if telemetry.hit_rpm is None else f"{telemetry.hit_rpm:.0f}"
            draw.text((0, 40), f"HIT {hit}  n={telemetry.strokes}", font=self._font, fill=255)
            if telemetry.current_a is not None:
                draw.text((0, 52), f"I {telemetry.current_a:.2f}A", font=self._font, fill=255)
            if telemetry.estop:
                draw.rectangle((96, 0, 127, 14), outline=255, fill=255)
                draw.text((98, 2), "STP", font=self._font, fill=0)

    def close(self) -> None:
        self._device.cleanup()


class PiControls:
    def __init__(self) -> None:
        from gpiozero import Button

        _use_pigpio_factory()
        self._fire = Button(config.FIRE_PIN, pull_up=True, bounce_time=0.05)
        self._home = Button(config.HOME_PIN, pull_up=True, bounce_time=0.05)
        self._estop = Button(config.ESTOP_PIN, pull_up=True, bounce_time=0.02)
        self._pot = None
        self._is_r = None
        self._is_l = None
        try:
            import adafruit_ads1x15.ads1115 as ADS
            import board
            import busio
            from adafruit_ads1x15.analog_in import AnalogIn

            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c, address=config.ADS1115_I2C_ADDR)
            self._pot = AnalogIn(ads, ADS.P0)
            self._is_r = AnalogIn(ads, ADS.P1)
            self._is_l = AnalogIn(ads, ADS.P2)
        except Exception:
            self._pot = None

    def power(self) -> float:
        if self._pot is None:
            return 0.4
        volts = max(0.0, min(3.3, self._pot.voltage))
        return volts / 3.3

    def fire_pressed(self) -> bool:
        return self._fire.is_pressed

    def home_pressed(self) -> bool:
        return self._home.is_pressed

    def estop(self) -> bool:
        # NO button to GND. Unwired pin stays high so bring-up is not stuck in ESTOP.
        # Real safety is a panel switch that cuts motor B+.
        return self._estop.is_pressed

    def current_amps(self) -> Optional[float]:
        if self._is_r is None or self._is_l is None:
            return None
        volts = max(self._is_r.voltage, self._is_l.voltage)
        return max(0.0, volts * config.CURRENT_AMPS_PER_VOLT)

    def close(self) -> None:
        self._fire.close()
        self._home.close()
        self._estop.close()
