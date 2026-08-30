"""Mock hardware for developing the app on Windows."""

from __future__ import annotations

import sys
import time
from typing import Optional

import config
from stroke_sim import Telemetry


class MockMotor:
    def __init__(self) -> None:
        self.duty = 0.0
        self._braking = False

    def set_duty(self, duty: float) -> None:
        self._braking = False
        self.duty = max(-1.0, min(1.0, duty))

    def brake(self) -> None:
        self._braking = True
        self.duty = 0.0

    def stop(self) -> None:
        self._braking = False
        self.duty = 0.0

    def close(self) -> None:
        self.stop()


class MockEncoder:
    def __init__(self, motor: MockMotor) -> None:
        self._motor = motor
        self._position = 0
        self._last = time.monotonic()
        self._rpm = 0.0

    @property
    def position(self) -> int:
        now = time.monotonic()
        dt = min(now - self._last, 0.05)
        self._last = now
        # 90 RPM at full duty so a dry-run stroke finishes in ~0.7 s.
        counts_per_sec = self._motor.duty * (90.0 / 60.0) * config.COUNTS_PER_REV
        if self._motor._braking:
            counts_per_sec = 0.0
        self._position += int(counts_per_sec * dt)
        self._rpm = abs(self._motor.duty) * 90.0
        return self._position

    def rpm(self) -> float:
        return self._rpm

    def set_home(self) -> None:
        self._position = 0

    def close(self) -> None:
        return


class MockDisplay:
    def render(self, telemetry: Telemetry) -> None:
        hit = ""
        if telemetry.hit_rpm is not None:
            hit = f"  hit {telemetry.hit_rpm:6.1f}{telemetry.target_name[:3]}"
        current = "" if telemetry.current_a is None else f"  {telemetry.current_a:4.1f}A"
        line = (
            f"\r{telemetry.state:<8}  "
            f"{telemetry.angle_deg:6.1f}°  "
            f"tgt {telemetry.target:6.1f}{telemetry.target_name[:3]}  "
            f"duty {telemetry.duty*100:5.1f}%  "
            f"rpm {telemetry.rpm:6.1f}"
            f"{current}{hit}  n={telemetry.strokes}   "
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def close(self) -> None:
        sys.stdout.write("\n")


class MockControls:
    """Keys: 1–9 power, space fire, h home, e e-stop, q quit."""

    def __init__(self, motor: Optional[MockMotor] = None) -> None:
        self._motor = motor
        self._power = 0.5
        self._estop = False
        self._fire = False
        self._home = False
        self._quit = False
        try:
            import msvcrt

            self._msvcrt = msvcrt
        except ImportError:
            self._msvcrt = None

    def _poll_keys(self) -> None:
        if self._msvcrt is None:
            return
        while self._msvcrt.kbhit():
            key = self._msvcrt.getwch()
            if key in "123456789":
                self._power = int(key) / 9.0
            elif key == "0":
                self._power = 0.0
            elif key in (" ", "\r"):
                self._fire = True
            elif key.lower() == "h":
                self._home = True
            elif key.lower() == "e":
                self._estop = not self._estop
            elif key.lower() == "q":
                self._quit = True

    def power(self) -> float:
        self._poll_keys()
        return self._power

    def fire_pressed(self) -> bool:
        self._poll_keys()
        fired, self._fire = self._fire, False
        return fired

    def home_pressed(self) -> bool:
        self._poll_keys()
        homed, self._home = self._home, False
        return homed

    def estop(self) -> bool:
        self._poll_keys()
        return self._estop

    def current_amps(self) -> Optional[float]:
        if self._motor is None:
            return None
        return abs(self._motor.duty) * 4.0

    def close(self) -> None:
        return

    @property
    def quit_requested(self) -> bool:
        self._poll_keys()
        return self._quit
