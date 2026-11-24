"""Read and validate live NMEA GPS coordinates from the Raspberry Pi UART."""

import time

import serial


def nmea_to_decimal(value, hemisphere):
    """Convert NMEA ddmm.mmmm / dddmm.mmmm coordinates to decimal degrees."""
    if not value or hemisphere not in ("N", "S", "E", "W"):
        return None

    try:
        degree_digits = 2 if hemisphere in ("N", "S") else 3
        degrees = int(value[:degree_digits])
        minutes = float(value[degree_digits:])

        if not 0 <= minutes < 60:
            return None

        coordinate = degrees + minutes / 60.0

        if hemisphere in ("S", "W"):
            coordinate = -coordinate

        limit = 90 if hemisphere in ("N", "S") else 180
        if abs(coordinate) > limit:
            return None

        return coordinate

    except (ValueError, TypeError):
        return None


def parse_gga(sentence):
    """Parse a GPGGA/GNGGA sentence. Return None if its fix is invalid."""
    fields = sentence.split("*", 1)[0].split(",")

    if not fields or fields[0] not in ("$GPGGA", "$GNGGA"):
        return None

    if len(fields) < 10:
        return None

    try:
        fix_quality = int(fields[6] or 0)
        satellites = int(fields[7] or 0)
        hdop = float(fields[8]) if fields[8] else None
    except ValueError:
        return None

    if fix_quality <= 0:
        return None

    latitude = nmea_to_decimal(fields[2], fields[3])
    longitude = nmea_to_decimal(fields[4], fields[5])

    if latitude is None or longitude is None:
        return None

    return {
        "latitude": latitude,
        "longitude": longitude,
        "fix_quality": fix_quality,
        "satellites": satellites,
        "hdop": hdop,
        "utc": fields[1],
    }


def read_gps_fix(port="/dev/serial0", baudrate=9600, timeout=30):
    """
    Wait up to timeout seconds for a valid GPS fix.

    Returns a dictionary containing the latest valid GGA reading,
    or None if no valid fix arrives in time.
    """
    deadline = time.monotonic() + timeout

    try:
        with serial.Serial(port, baudrate, timeout=1) as gps:
            while time.monotonic() < deadline:
                raw = gps.readline()

                if not raw:
                    continue

                sentence = raw.decode("ascii", errors="replace").strip()
                fix = parse_gga(sentence)

                if fix is not None:
                    return fix

    except serial.SerialException as exc:
        raise RuntimeError(f"Could not read GPS serial port {port}: {exc}") from exc

    return None
