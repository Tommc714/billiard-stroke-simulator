"""Hardware interfaces. Live Pi drivers load lazily so Windows dry-run works."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class Telemetry:
    power: float
    encoder: int
    angle_deg: float
    duty: float
    rpm: float
    current_a: Optional[float]
    state: str
    estop: bool
    hit_rpm: Optional[float] = None
    hit_current: Optional[float] = None
    strokes: int = 0
    target: float = 0.0
    target_name: str = "rpm"


class Motor(Protocol):
    duty: float

    def set_duty(self, duty: float) -> None:
        """Signed duty: +forward, -reverse, 0 coast."""

    def brake(self) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class Encoder(Protocol):
    @property
    def position(self) -> int: ...

    def rpm(self) -> float: ...

    def set_home(self) -> None: ...

    def close(self) -> None: ...


class Display(Protocol):
    def render(self, telemetry: Telemetry) -> None: ...

    def close(self) -> None: ...


class Controls(Protocol):
    def power(self) -> float: ...

    def fire_pressed(self) -> bool: ...

    def home_pressed(self) -> bool: ...

    def estop(self) -> bool: ...

    def current_amps(self) -> Optional[float]: ...

    def close(self) -> None: ...
