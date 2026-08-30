# Build the machine, put the code on the Pi

## Buy before the motor is live

- IBT-2 / BTS7960 H-bridge (do not wire the motor to Pi GPIO)
- Dupont jumper wires
- Two 1.5 kΩ resistors (encoder A/B pull-up to 3.3 V)
- 6 mm shaft coupling for the Taiss encoder to the crank
- ADS1115 I2C 16-bit ADC breakout (Adafruit 1085 or generic; not ADS1015). Powers from 3.3 V and shares SDA/SCL with the OLED. Knob wiper goes to A0.
- Official USB-C 5 V supply for the Pi (not the 3–24 V brick)

## Build order

1. Couple the encoder to the **crank** shaft (6 mm). The last 8 inches of the cue stay free — clamp behind that.
2. Wire **only the OLED** to the Pi. Copy the code. Run `--mode oled`.
3. Wire the **encoder** (5 V / GND / A / B with 1.5 kΩ to 3.3 V). Hand-turn the crank. Run `--mode encoder`. Aim for ~2400 counts per turn.
4. Set the bench supply low (~9 V if the motor is unlabeled). Wire the **H-bridge**. Common ground with the Pi. Then `--mode jog`.
5. Fire button GPIO23 to GND, home GPIO24 to GND. Then `python3 main.py`.

Pin map is in `config.py`. Encoder white = A, green = B. Never tie A or B to 5 V.

## Copy the code (this Windows PC)

Pi and PC on the same network, SSH enabled on the Pi:

```powershell
cd "C:\Users\tommc\Billiard Stroke Simulator"
.\scripts\copy-to-pi.ps1
```

If the hostname is not `raspberrypi.local`, pass the address:

```powershell
.\scripts\copy-to-pi.ps1 pi@192.168.1.50
```

USB instead: copy the project folder onto a stick, then on the Pi:

```bash
cp -r /media/pi/*/Billiard\ Stroke\ Simulator ~/billiard-stroke
```

## On the Pi

```bash
cd ~/billiard-stroke
chmod +x scripts/setup-pi.sh
./scripts/setup-pi.sh
source .venv/bin/activate
python3 main.py --mode oled
python3 main.py --mode encoder
```

`--mode jog` and `python3 main.py` wait until the H-bridge is wired.
