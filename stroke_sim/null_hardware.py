"""No-op hardware so OLED, encoder, and motor can be brought up separately."""

from __future__ import annotations

from typing import Optional

from stroke_sim import Telemetry


class NullMotor:
    duty = 0.0

    def set_duty(self, duty: float) -> None:
        self.duty = 0.0

    def brake(self) -> None:
        self.duty = 0.0

    def stop(self) -> None:
        self.duty = 0.0

    def close(self) -> None:
        return


class NullEncoder:
    @property
    def position(self) -> int:
        return 0

    def rpm(self) -> float:
        return 0.0

    def set_home(self) -> None:
        return

    def close(self) -> None:
        return


class NullDisplay:
    def render(self, telemetry: Telemetry) -> None:
        return

    def close(self) -> None:
        return


class NullControls:
    def power(self) -> float:
        return 0.4

    def fire_pressed(self) -> bool:
        return False

    def home_pressed(self) -> bool:
        return False

    def estop(self) -> bool:
        return False

    def current_amps(self) -> Optional[float]:
        return None

    def close(self) -> None:
        return
