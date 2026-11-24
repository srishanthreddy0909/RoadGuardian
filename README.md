# RoadGuardian

A Raspberry Pi-based driver and road risk monitoring prototype.

## Implemented
- GPS UART monitoring at 9600 baud.
- GPS accident-zone detection using Haversine distance.
- Configurable accident-zone threshold.
- Random Forest risk prediction.
- Android notifications through ntfy.
- GPS geofence, overspeed and signal-loss alert worker.
- Ultrasonic sensor module (software implementation).

## Current operation
Driver and road status are entered manually.
Camera-based detection is intentionally excluded from this release.

## Hardware

### GPS module
- GPS TX -> Pi GPIO15 / RXD1
- GPS GND -> Pi GND
- GPS VCC -> module-supported supply voltage
- GPIO15 requires ALT5 for UART RX.

Persistent Pi configuration:
`gpio=15=a5` in `/boot/firmware/config.txt`.

### HC-SR04 ultrasonic sensor
- VCC -> 5V
- GND -> common GND
- TRIG -> BCM GPIO16 (physical pin 36)
- ECHO -> BCM GPIO18 (physical pin 12), through a suitable voltage divider or 3.3V-compatible level shifter.

IMPORTANT: Never connect the HC-SR04 5V ECHO output directly to Raspberry Pi GPIO. Real sensor testing is pending suitable voltage protection.

## Notifications
The ntfy topic is stored outside this repository at:
`~/.config/neurodrive/ntfy_topic`

Never commit notification topics, tokens or credentials.

## Camera status
Camera-dependent modules are excluded from this release. They may be added after the camera hardware issue is resolved.

## Validation status
GPS reception, GPS monitoring, zone evaluation, ML prediction and MEDIUM/HIGH ML phone notifications have been tested on the Raspberry Pi.

GPS automatic event notifications still require individual tests. Ultrasonic hardware measurements and obstacle phone alerts remain pending hardware protection and testing.

## Software setup

On Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-rpi.gpio python3-serial python3-numpy python3-scipy python3-sklearn python3-joblib python3-pytest
```
