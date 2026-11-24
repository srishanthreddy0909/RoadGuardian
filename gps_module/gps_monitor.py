"""Background GPS monitor for RoadGuardian."""

import threading
import time
import serial

from gps_module.gps_reader import parse_gga


def parse_rmc(sentence):
    """Extract GPS speed from a valid RMC sentence."""
    fields = sentence.split("*", 1)[0].split(",")

    if not fields or fields[0] not in ("$GPRMC", "$GNRMC"):
        return None

    if len(fields) < 9 or fields[2] != "A":
        return None

    try:
        knots = float(fields[7]) if fields[7] else 0.0
        speed_kmh = knots * 1.852

        if not 0 <= speed_kmh <= 300:
            return None

        return speed_kmh
    except ValueError:
        return None


class GPSMonitor:
    def __init__(
        self,
        port="/dev/serial0",
        baudrate=9600,
        stale_after=5,
        min_satellites=3,
        max_hdop=10.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.stale_after = stale_after
        self.min_satellites = min_satellites
        self.max_hdop = max_hdop

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._latest = None
        self._fix_active = False
        self._error = None
        self._rmc_speed = None
        self._rmc_time = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name="RoadGuardian-GPS",
        )
        self._thread.start()

    def _read_loop(self):
        try:
            with serial.Serial(
                self.port,
                self.baudrate,
                timeout=1,
            ) as gps:

                while not self._stop_event.is_set():
                    raw = gps.readline()

                    if not raw:
                        continue

                    sentence = raw.decode(
                        "ascii", errors="replace"
                    ).strip()

                    if sentence.startswith(("$GPRMC", "$GNRMC")):
                        speed = parse_rmc(sentence)

                        with self._lock:
                            self._rmc_speed = speed
                            self._rmc_time = time.monotonic()

                        continue

                    if not sentence.startswith(("$GPGGA", "$GNGGA")):
                        continue

                    fix = parse_gga(sentence)

                    if fix is None:
                        with self._lock:
                            self._fix_active = False
                        continue

                    hdop = fix["hdop"]
                    satellites = fix["satellites"]

                    usable = (
                        satellites >= self.min_satellites
                        and hdop is not None
                        and hdop <= self.max_hdop
                    )

                    with self._lock:
                        if usable:
                            fix["speed_kmh"] = (
                                self._rmc_speed
                                if time.monotonic() - self._rmc_time <= 2.5
                                else None
                            )
                            fix["_received_monotonic"] = time.monotonic()

                            self._latest = fix
                            self._fix_active = True
                            self._error = None
                        else:
                            self._fix_active = False

        except (serial.SerialException, OSError) as exc:
            with self._lock:
                self._fix_active = False
                self._error = str(exc)

    def get_fix(self):
        with self._lock:
            if not self._fix_active or self._latest is None:
                return None

            fix = dict(self._latest)
            age = time.monotonic() - fix["_received_monotonic"]

            if age > self.stale_after:
                return None

            fix.pop("_received_monotonic", None)
            fix["age_seconds"] = age
            return fix

    def get_error(self):
        with self._lock:
            return self._error

    def stop(self):
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
