"""Pin map and tuning constants for the Raspberry Pi 4B.

Purpose: measure the english collision — squirt (endmass/ferrules), spin
(tips/grip), offset, and miscue — from a repeatable stroke. Not a break
machine.

Squirt is read on the end rail versus a center-ball zero. Spin is a required
output; its sensor comes after the stroke is consistent. Hold the cue behind
the last 5–8 in so the fixture does not fake endmass. Lock speed so rail
marks and later spin numbers are comparable.

This machine is a crank-slider, not a linear actuator. One crank revolution
extends AND retracts the slider. Reverse is only for rocker mode, jogging,
and un-jamming.

Encoder Taiss E38S6-600-24G is NPN open-collector. Power at 5 V. Pull A/B
to 3.3 V with 1–2.2 kΩ. Never tie A or B to VCC — that kills the outputs.

Do not wire the motor to GPIO. Use an H-bridge. Common-ground the Pi,
driver, encoder, and ADC. Power the Pi from its own USB-C supply.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"

# --- Encoder (BCM) ---
ENCODER_PIN_A = 17  # white, board pin 11
ENCODER_PIN_B = 27  # green, board pin 13
ENCODER_PPR = 600
ENCODER_PULL_UP = True  # extra to the required external 1–2.2 kΩ to 3.3 V
COUNTS_PER_REV = ENCODER_PPR * 4  # 4× quadrature = 2400 counts / crank rev

# --- Motor driver IBT-2 / BTS7960 (BCM) ---
MOTOR_RPWM = 12  # board 32, PWM0
MOTOR_LPWM = 13  # board 33, PWM1
MOTOR_R_EN = 16  # board 36
MOTOR_L_EN = 26  # board 37
MOTOR_PWM_HZ = 20000
MOTOR_MAX_DUTY = 0.6  # raise after you measure stall current at your voltage
# True if +duty makes encoder counts go down (stroke would never hit +2400).
MOTOR_INVERT = True
# Jog is a creep, not a stroke. 6% of 9 V will not turn most motors; 25% is still well under MAX.
JOG_DUTY = 0.25

# --- User controls (BCM) ---
FIRE_PIN = 23  # board 16, button to GND
HOME_PIN = 24  # board 18, button to GND — sets encoder zero (cue-back)
ESTOP_PIN = 22  # board 15, software backup; real e-stop must cut motor B+

# --- I2C ---
OLED_I2C_ADDR = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64
ADS1115_I2C_ADDR = 0x48
POT_ADC_CHANNEL = 0
CURRENT_R_CHANNEL = 1  # IBT-2 R_IS via 3.3 V clamp
CURRENT_L_CHANNEL = 2  # IBT-2 L_IS via 3.3 V clamp

# Current-sense scale. IBT-2 IS pins vary by board resistor (often 10 kΩ).
# Nominal BTS7960: I_load = V_is * 8500 / R_is.  10 kΩ → ~0.85 A per volt.
# Calibrate against a meter before trusting force numbers.
CURRENT_AMPS_PER_VOLT = 0.85

# --- Stroke profile ---
# "full_rev": one crank turn is one complete stroke cycle, then stop.
# "rocker": drive forward STROKE_COUNTS, then reverse back to start.
STROKE_MODE = "full_rev"
STROKE_COUNTS = COUNTS_PER_REV
HIT_ANGLE_DEG = 85.0  # mid-stroke; keep in 70–100°
HIT_WINDOW_DEG = 8.0
RETURN_DUTY_SCALE = 0.35
RAMP_SECONDS = 0.12
STALL_SECONDS = 0.35
STALL_MIN_DUTY = 0.08
STALL_MIN_COUNTS = 4
BRAKE_SECONDS = 0.08

# --- Repeatability (iterative learning) ---
# "speed": pot sets target RPM at the hit window (works with encoder only).
# "current": pot sets target amps at the hit window (needs IS pins + ADS1115).
TARGET_MODE = "speed"
TARGET_RPM_MIN = 20.0
TARGET_RPM_MAX = 180.0
TARGET_CURRENT_MIN = 0.3
TARGET_CURRENT_MAX = 8.0
ILC_GAIN = 0.08
ILC_ENABLED = True
