"""Ultrasonic distance classification and phone alerts."""

import math
import time

from integration.ntfy_notifier import send_notification


def classify_distance(distance_cm, warning_cm=20.0, critical_cm=10.0):
    """Classify a distance reading without accessing GPIO."""
    if distance_cm is None:
        return {
            "status": "UNAVAILABLE",
            "obstacle": False,
            "distance_cm": None,
        }

    try:
        distance = float(distance_cm)
    except (TypeError, ValueError):
        return {
            "status": "INVALID",
            "obstacle": False,
            "distance_cm": None,
        }

    if not math.isfinite(distance) or distance < 0:
        return {
            "status": "INVALID",
            "obstacle": False,
            "distance_cm": None,
        }

    if distance <= critical_cm:
        status = "CRITICAL"
    elif distance <= warning_cm:
        status = "WARNING"
    else:
        status = "CLEAR"

    return {
        "status": status,
        "obstacle": status in ("WARNING", "CRITICAL"),
        "distance_cm": distance,
    }


class ObstacleAlertManager:
    def __init__(
        self,
        warning_cm=20.0,
        critical_cm=10.0,
        clear_margin_cm=3.0,
        cooldown_seconds=60.0,
        notifier=None,
    ):
        if not 0 < critical_cm < warning_cm:
            raise ValueError("Require 0 < critical distance < warning distance.")
        if clear_margin_cm < 0 or cooldown_seconds < 0:
            raise ValueError("Margin and cooldown cannot be negative.")

        self.warning_cm = float(warning_cm)
        self.critical_cm = float(critical_cm)
        self.clear_margin_cm = float(clear_margin_cm)
        self.cooldown_seconds = float(cooldown_seconds)
        self.notifier = notifier or send_notification

        self._active_level = None
        self._last_sent_at = float("-inf")

    def process_distance(self, distance_cm, now=None):
        """Classify a reading and notify on obstacle entry/escalation."""
        now = time.monotonic() if now is None else float(now)

        result = classify_distance(
            distance_cm,
            warning_cm=self.warning_cm,
            critical_cm=self.critical_cm,
        )

        if result["status"] in ("UNAVAILABLE", "INVALID"):
            return result

        distance = result["distance_cm"]

        # Require a margin above the warning threshold to clear an alert.
        clear_threshold = self.warning_cm + self.clear_margin_cm

        if not result["obstacle"] and distance > clear_threshold:
            self._active_level = None
            return result

        if not result["obstacle"]:
            # Within the hysteresis band: retain the previous active state.
            result["obstacle"] = self._active_level is not None
            if self._active_level:
                result["status"] = self._active_level
            return result

        level = result["status"]

        # Critical is an escalation over Warning.
        escalated = self._active_level == "WARNING" and level == "CRITICAL"
        first_alert = self._active_level is None
        cooldown_expired = now - self._last_sent_at >= self.cooldown_seconds

        if first_alert or escalated or cooldown_expired:
            priority = 5 if level == "CRITICAL" else 4
            title = f"ROADGUARDIAN - OBSTACLE {level}"
            message = (
                f"Obstacle detected at {distance:.1f} cm.\n"
                f"Alert level: {level}.\n"
                "Reduce speed and maintain a safe distance."
            )

            try:
                sent = self.notifier(
                    title,
                    message,
                    priority=priority,
                    tags="warning",
                )
            except Exception as exc:
                print("[OBSTACLE ALERT] Notification error:", exc)
                sent = False

            if sent:
                self._last_sent_at = now
                self._active_level = level
                print(f"[OBSTACLE ALERT] {title} sent to phone.")

        result["obstacle"] = True
        return result
