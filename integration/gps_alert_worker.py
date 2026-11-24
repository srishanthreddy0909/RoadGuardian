"""Background GPS alerts: geofence, overspeed and signal loss."""

import math
import threading
import time

from gps_module.zone_detector import evaluate_zone
from integration.ntfy_notifier import send_notification


class GPSAlertWorker:
    def __init__(
        self,
        gps_monitor,
        speed_limit_kmh=40.0,
        poll_interval=2.0,
        gps_lost_after=15.0,
        zone_cooldown_seconds=300.0,
        overspeed_confirm_seconds=5.0,
        notifier=None,
        zone_evaluator=None,
    ):
        if speed_limit_kmh <= 0:
            raise ValueError("Speed limit must be positive.")
        if poll_interval <= 0 or gps_lost_after <= 0:
            raise ValueError("Polling and GPS timeout must be positive.")

        self.gps_monitor = gps_monitor
        self.speed_limit_kmh = float(speed_limit_kmh)
        self.poll_interval = float(poll_interval)
        self.gps_lost_after = float(gps_lost_after)
        self.zone_cooldown_seconds = float(zone_cooldown_seconds)
        self.overspeed_confirm_seconds = float(overspeed_confirm_seconds)

        self.notifier = notifier or send_notification
        self.zone_evaluator = zone_evaluator or evaluate_zone

        self._stop_event = threading.Event()
        self._thread = None

        self._gps_unavailable_since = None
        self._gps_lost_sent = False
        self._zone_last_sent = {}
        self._active_zone = None
        self._speed_over_since = None
        self._speed_alert_sent = False

    def _notify(self, title, message, priority, tags="warning"):
        try:
            success = self.notifier(
                title,
                message,
                priority=priority,
                tags=tags,
            )
            print(
                f"[NTFY] {title}: "
                f"{'sent' if success else 'delivery failed'}"
            )
            return bool(success)
        except Exception as exc:
            print(f"[NTFY] Notification error: {exc}")
            return False

    def process_no_fix(self, now=None):
        """Process a missing GPS fix. Exposed for deterministic tests."""
        now = time.monotonic() if now is None else float(now)

        self._speed_over_since = None
        self._speed_alert_sent = False
        self._active_zone = None

        if self._gps_unavailable_since is None:
            self._gps_unavailable_since = now

        if (
            not self._gps_lost_sent
            and now - self._gps_unavailable_since >= self.gps_lost_after
        ):
            sent = self._notify(
                "ROADGUARDIAN - GPS LOST",
                "GPS signal unavailable. Location monitoring is interrupted.",
                priority=4,
            )
            if sent:
                self._gps_lost_sent = True

    def process_fix(self, fix, now=None):
        """Process one valid GPS fix. Exposed for deterministic tests."""
        now = time.monotonic() if now is None else float(now)

        self._gps_unavailable_since = None

        if self._gps_lost_sent:
            restored = self._notify(
                "ROADGUARDIAN - GPS RESTORED",
                "GPS signal restored. Monitoring has resumed.",
                priority=3,
                tags="white_check_mark",
            )
            if restored:
                self._gps_lost_sent = False

        # Accident-zone notification.
        try:
            result = self.zone_evaluator(
                fix["latitude"],
                fix["longitude"],
                verbose=False,
            )

            danger = (
                result["within_threshold"]
                and result["risk_level"] in ("HIGH", "MEDIUM")
            )

            if danger:
                zone = result["location"]
                last_sent = self._zone_last_sent.get(zone, float("-inf"))

                if now - last_sent >= self.zone_cooldown_seconds:
                    level = result["risk_level"]
                    priority = 5 if level == "HIGH" else 4

                    sent = self._notify(
                        f"ROADGUARDIAN - {level} RISK",
                        f"Accident-prone area: {zone}\n"
                        f"Distance: {result['distance_km'] * 1000:.0f} metres.\n"
                        "Please exercise caution.",
                        priority=priority,
                    )

                    if sent:
                        self._zone_last_sent[zone] = now

                self._active_zone = zone
            else:
                self._active_zone = None

        except Exception as exc:
            print("[GPS ALERT] Zone detection error:", exc)

        # Overspeed notification.
        speed = fix.get("speed_kmh")

        if speed is None:
            self._speed_over_since = None
            self._speed_alert_sent = False
            return

        try:
            speed = float(speed)
        except (TypeError, ValueError):
            self._speed_over_since = None
            self._speed_alert_sent = False
            return

        if not math.isfinite(speed) or speed < 0:
            self._speed_over_since = None
            self._speed_alert_sent = False
            return

        if speed >= self.speed_limit_kmh:
            if self._speed_over_since is None:
                self._speed_over_since = now

            if (
                now - self._speed_over_since >= self.overspeed_confirm_seconds
                and not self._speed_alert_sent
            ):
                sent = self._notify(
                    "ROADGUARDIAN - OVERSPEED",
                    f"GPS speed: {speed:.1f} km/h\n"
                    f"Configured demo limit: {self.speed_limit_kmh:.1f} km/h.\n"
                    "Please check your speed.",
                    priority=5,
                )
                if sent:
                    self._speed_alert_sent = True

        elif speed < self.speed_limit_kmh - 3:
            self._speed_over_since = None
            self._speed_alert_sent = False

    def process_once(self, now=None):
        """Read the monitor once and process its current state."""
        fix = self.gps_monitor.get_fix()

        if fix is None:
            self.process_no_fix(now)
        else:
            self.process_fix(fix, now)

    def _run(self):
        while not self._stop_event.is_set():
            self.process_once()
            self._stop_event.wait(self.poll_interval)

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="RoadGuardian-Alerts",
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
