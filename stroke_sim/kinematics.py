"""Slider-crank helpers. Angles are degrees from the homed cue-back position."""

from __future__ import annotations

import config


def wrap_deg(angle: float) -> float:
    return angle % 360.0


def counts_to_deg(counts: int) -> float:
    return wrap_deg(counts * 360.0 / config.COUNTS_PER_REV)


def deg_to_counts(deg: float) -> int:
    return int(round(deg / 360.0 * config.COUNTS_PER_REV))


def in_hit_window(angle_deg: float) -> bool:
    lo = config.HIT_ANGLE_DEG - config.HIT_WINDOW_DEG / 2.0
    hi = config.HIT_ANGLE_DEG + config.HIT_WINDOW_DEG / 2.0
    angle = wrap_deg(angle_deg)
    if lo < 0:
        return angle >= wrap_deg(lo) or angle <= hi
    if hi >= 360:
        return angle >= lo or angle <= wrap_deg(hi)
    return lo <= angle <= hi
