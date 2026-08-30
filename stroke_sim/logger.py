"""Append-only CSV of completed strokes — this is how repeatability is proven."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config


FIELDS = [
    "utc",
    "stroke",
    "mode",
    "target_name",
    "target",
    "duty",
    "hit_rpm",
    "hit_current_a",
    "encoder_at_hit",
    "angle_deg",
    "offset_mm",
    "rail_hit_mm",
    "spin",
    "ferrule",
    "tip",
    "notes",
]


class StrokeLog:
    def __init__(self, path: Optional[Path] = None) -> None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or (config.LOG_DIR / "strokes.csv")
        self._new = not self.path.exists()

    def record(
        self,
        stroke: int,
        target_name: str,
        target: float,
        duty: float,
        hit_rpm: Optional[float],
        hit_current: Optional[float],
        encoder_at_hit: Optional[int],
        angle_deg: float,
    ) -> None:
        with self.path.open("a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if self._new:
                writer.writeheader()
                self._new = False
            writer.writerow(
                {
                    "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "stroke": stroke,
                    "mode": config.STROKE_MODE,
                    "target_name": target_name,
                    "target": f"{target:.4f}",
                    "duty": f"{duty:.4f}",
                    "hit_rpm": "" if hit_rpm is None else f"{hit_rpm:.2f}",
                    "hit_current_a": "" if hit_current is None else f"{hit_current:.3f}",
                    "encoder_at_hit": "" if encoder_at_hit is None else encoder_at_hit,
                    "angle_deg": f"{angle_deg:.1f}",
                    "offset_mm": "",
                    "rail_hit_mm": "",
                    "spin": "",
                    "ferrule": "",
                    "tip": "",
                    "notes": "",
                }
            )
