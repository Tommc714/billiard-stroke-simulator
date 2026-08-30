"""Stroke state machine: idle → stroke → (rocker return) → idle.

full_rev: one crank turn is one complete extend+retract cycle, then stop.
rocker: drive forward, then reverse back to the start angle.

PWM is adjusted stroke-to-stroke (iterative learning) so the value sampled
inside the hit window — RPM or current — converges on the pot target.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Optional

import config
from stroke_sim import Controls, Display, Encoder, Motor, Telemetry
from stroke_sim.kinematics import counts_to_deg, deg_to_counts
from stroke_sim.logger import StrokeLog


class State(str, Enum):
    IDLE = "IDLE"
    STROKE = "STROKE"
    RETURN = "RETURN"
    BRAKE = "BRAKE"
    ESTOP = "ESTOP"
    STALL = "STALL"


class StrokeController:
    def __init__(
        self,
        motor: Motor,
        encoder: Encoder,
        display: Display,
        controls: Controls,
        log: Optional[StrokeLog] = None,
    ) -> None:
        self.motor = motor
        self.encoder = encoder
        self.display = display
        self.controls = controls
        self.log = log or StrokeLog()
        self.state = State.IDLE
        self._start_pos = 0
        self._duty_cmd = 0.0
        self._learned_duty = 0.25
        self._last_fire = False
        self._last_home = False
        self._stroke_t0 = 0.0
        self._brake_t0 = 0.0
        self._move_pos = 0
        self._move_t = 0.0
        self._captured = False
        self._hit_rpm: Optional[float] = None
        self._hit_current: Optional[float] = None
        self._hit_encoder: Optional[int] = None
        self._strokes = 0
        self._last_hit_rpm: Optional[float] = None
        self._last_hit_current: Optional[float] = None

    def _target(self, power: float) -> tuple[str, float]:
        if config.TARGET_MODE == "current":
            span = config.TARGET_CURRENT_MAX - config.TARGET_CURRENT_MIN
            return "amps", config.TARGET_CURRENT_MIN + power * span
        span = config.TARGET_RPM_MAX - config.TARGET_RPM_MIN
        return "rpm", config.TARGET_RPM_MIN + power * span

    def _ilc_update(self, target_name: str, target: float) -> None:
        if not config.ILC_ENABLED:
            return
        if target_name == "amps":
            measured = self._hit_current
            scale = config.TARGET_CURRENT_MAX
        else:
            measured = self._hit_rpm
            scale = config.TARGET_RPM_MAX
        if measured is None or scale <= 0:
            return
        error = (target - measured) / scale
        self._learned_duty = max(
            0.05,
            min(config.MOTOR_MAX_DUTY, self._learned_duty + config.ILC_GAIN * error),
        )

    def _watchdog(self, pos: int, now: float) -> bool:
        if abs(self.motor.duty) < config.STALL_MIN_DUTY:
            self._move_pos = pos
            self._move_t = now
            return False
        if abs(pos - self._move_pos) >= config.STALL_MIN_COUNTS:
            self._move_pos = pos
            self._move_t = now
            return False
        return (now - self._move_t) >= config.STALL_SECONDS

    def _ramp_duty(self, goal: float, now: float) -> float:
        if config.RAMP_SECONDS <= 0:
            return goal
        elapsed = now - self._stroke_t0
        blend = min(1.0, elapsed / config.RAMP_SECONDS)
        return goal * blend

    def _finish_stroke(self, target_name: str, target: float, angle_deg: float) -> None:
        self._strokes += 1
        self._last_hit_rpm = self._hit_rpm
        self._last_hit_current = self._hit_current
        self.log.record(
            stroke=self._strokes,
            target_name=target_name,
            target=target,
            duty=self._duty_cmd,
            hit_rpm=self._hit_rpm,
            hit_current=self._hit_current,
            encoder_at_hit=self._hit_encoder,
            angle_deg=angle_deg,
        )
        self._ilc_update(target_name, target)

    def step(self) -> Telemetry:
        now = time.monotonic()
        power = self.controls.power()
        pos = self.encoder.position
        angle = counts_to_deg(pos)
        current = self.controls.current_amps()
        target_name, target = self._target(power)

        if self.controls.estop():
            self.motor.stop()
            self.state = State.ESTOP
        elif self.state == State.ESTOP and not self.controls.estop():
            self.state = State.IDLE

        home = self.controls.home_pressed()
        fire = self.controls.fire_pressed()
        rising_fire = fire and not self._last_fire
        self._last_fire = fire

        if self.state == State.STALL and (rising_fire or home):
            self.state = State.IDLE
            rising_fire = False

        if home and not self._last_home and self.state == State.IDLE:
            self.encoder.set_home()
            pos = 0
            angle = 0.0
        self._last_home = home

        if self.state == State.IDLE and rising_fire and power > 0.02:
            self._start_pos = pos
            self._stroke_t0 = now
            self._move_pos = pos
            self._move_t = now
            self._captured = False
            self._hit_rpm = None
            self._hit_current = None
            self._hit_encoder = None
            # Seed from the knobs on the first shot; ILC owns later shots.
            if self._strokes == 0:
                self._learned_duty = max(0.08, power * config.MOTOR_MAX_DUTY)
            self._duty_cmd = self._learned_duty
            self.state = State.STROKE

        if self.state in (State.STROKE, State.RETURN) and self._watchdog(pos, now):
            self.motor.stop()
            self.state = State.STALL

        if self.state == State.STROKE:
            self.motor.set_duty(self._ramp_duty(self._duty_cmd, now))
            hit_at = self._start_pos + deg_to_counts(config.HIT_ANGLE_DEG)
            if not self._captured and pos >= hit_at:
                self._hit_rpm = self.encoder.rpm()
                self._hit_current = current
                self._hit_encoder = pos
                self._captured = True
            traveled = pos - self._start_pos
            if traveled >= config.STROKE_COUNTS:
                self._finish_stroke(target_name, target, angle)
                if config.STROKE_MODE == "rocker":
                    self._stroke_t0 = now
                    self.state = State.RETURN
                else:
                    self.motor.brake()
                    self._brake_t0 = now
                    self.state = State.BRAKE

        if self.state == State.RETURN:
            self.motor.set_duty(-self._ramp_duty(self._duty_cmd * config.RETURN_DUTY_SCALE, now))
            if pos <= self._start_pos:
                self.motor.brake()
                self._brake_t0 = now
                self.state = State.BRAKE

        if self.state == State.BRAKE:
            self.motor.brake()
            if now - self._brake_t0 >= config.BRAKE_SECONDS:
                self.motor.stop()
                self.state = State.IDLE

        if self.state == State.IDLE:
            self.motor.stop()

        telemetry = Telemetry(
            power=power,
            encoder=pos,
            angle_deg=angle,
            duty=self.motor.duty,
            rpm=self.encoder.rpm(),
            current_a=current,
            state=self.state.value,
            estop=self.state in (State.ESTOP, State.STALL),
            hit_rpm=self._last_hit_rpm,
            hit_current=self._last_hit_current,
            strokes=self._strokes,
            target=target,
            target_name=target_name,
        )
        self.display.render(telemetry)
        return telemetry

    def run(self, hz: float = 50.0) -> None:
        period = 1.0 / hz
        try:
            while True:
                started = time.monotonic()
                self.step()
                if getattr(self.controls, "quit_requested", False):
                    break
                remaining = period - (time.monotonic() - started)
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            self.motor.stop()
            self.motor.close()
            self.encoder.close()
            self.display.close()
            self.controls.close()
