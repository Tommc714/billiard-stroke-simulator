"""Billiard cue stroke simulator.

Windows:
    python main.py --dry-run

Raspberry Pi 4B (after scripts/setup-pi.sh):
    source ~/billiard-stroke/.venv/bin/activate
    sudo pigpiod
    python3 main.py --mode oled
    python3 main.py --mode encoder
    python3 main.py --mode jog
    python3 main.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def build_hardware(dry_run: bool, mode: str):
    if dry_run:
        from stroke_sim.mock_hardware import MockControls, MockDisplay, MockEncoder, MockMotor

        motor = MockMotor()
        return motor, MockEncoder(motor), MockDisplay(), MockControls(motor)

    from stroke_sim.null_hardware import NullControls, NullDisplay, NullEncoder, NullMotor
    from stroke_sim.pi_hardware import PiControls, PiDisplay, PiEncoder, PiMotor

    motor = NullMotor()
    encoder = NullEncoder()
    display = NullDisplay()
    controls = NullControls()

    if mode in ("stroke", "jog"):
        motor = PiMotor()
    if mode in ("stroke", "jog", "encoder"):
        encoder = PiEncoder()
    if mode in ("stroke", "oled"):
        display = PiDisplay()
    if mode in ("stroke", "jog"):
        controls = PiControls()
    return motor, encoder, display, controls


def _running(controls) -> bool:
    return not getattr(controls, "quit_requested", False)


def run_encoder_watch(dry_run: bool) -> int:
    motor, encoder, display, controls = build_hardware(dry_run, "encoder")
    print("Encoder watch. Turn the crank by hand. Ctrl+C to quit.")
    try:
        last = None
        while _running(controls):
            pos = encoder.position
            if pos != last:
                print(f"counts={pos:8d}  rpm={encoder.rpm():7.1f}")
                last = pos
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        encoder.close()
        motor.close()
        display.close()
        controls.close()
    return 0


def run_oled_watch(dry_run: bool) -> int:
    from stroke_sim import Telemetry

    motor, encoder, display, controls = build_hardware(dry_run, "oled")
    print("OLED test. Ctrl+C to quit.")
    try:
        t0 = time.monotonic()
        while _running(controls):
            elapsed = time.monotonic() - t0
            display.render(
                Telemetry(
                    power=0.4,
                    encoder=0,
                    angle_deg=(elapsed * 40) % 360,
                    duty=0.0,
                    rpm=0.0,
                    current_a=None,
                    state="OLED",
                    estop=False,
                    target=0.0,
                    target_name="rpm",
                )
            )
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()
    finally:
        motor.close()
        encoder.close()
        display.close()
        controls.close()
    return 0


def run_jog(dry_run: bool) -> int:
    motor, encoder, display, controls = build_hardware(dry_run, "jog")
    print("Jog: pot sets slow duty (15% cap). Ctrl+C to quit.")
    try:
        while _running(controls):
            if controls.estop():
                motor.stop()
            else:
                motor.set_duty(controls.power() * 0.15)
            print(
                f"\rduty {motor.duty*100:5.1f}%  enc {encoder.position:8d}  rpm {encoder.rpm():6.1f}   ",
                end="",
            )
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        motor.stop()
        motor.close()
        encoder.close()
        display.close()
        controls.close()
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Cue stroke simulator")
    parser.add_argument("--dry-run", action="store_true", help="Mock hardware")
    parser.add_argument(
        "--mode",
        choices=("stroke", "encoder", "oled", "jog"),
        default="stroke",
        help="oled and encoder do not need the motor driver",
    )
    args = parser.parse_args()
    if sys.platform == "win32" and not args.dry_run:
        print("On Windows, pass --dry-run. Live GPIO only runs on the Pi.")
        return 2

    if args.mode == "encoder":
        return run_encoder_watch(args.dry_run)
    if args.mode == "oled":
        return run_oled_watch(args.dry_run)
    if args.mode == "jog":
        return run_jog(args.dry_run)

    from stroke_sim.controller import StrokeController

    motor, encoder, display, controls = build_hardware(args.dry_run, "stroke")
    if args.dry_run:
        print("Dry run. 1-9 = power, space = fire, h = home, e = e-stop, q = quit")
    try:
        StrokeController(motor, encoder, display, controls).run()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
