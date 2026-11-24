"""Phone notifications for RoadGuardian ML risk predictions."""

import time
from integration.ntfy_notifier import send_notification


class RiskAlertManager:
    def __init__(self, cooldown_seconds=300):
        self.cooldown_seconds = cooldown_seconds
        self.last_level = None
        self.last_sent_at = 0.0

    def notify_if_needed(self, risk, driver_status, road_status):
        try:
            level = int(risk)
        except (TypeError, ValueError):
            return False

        # SAFE predictions do not need phone alerts.
        if level == 0:
            self.last_level = 0
            self.last_sent_at = 0.0
            return False

        if level not in (1, 2):
            return False

        now = time.monotonic()
        changed = level != self.last_level
        cooldown_expired = (
            now - self.last_sent_at >= self.cooldown_seconds
        )

        if not changed and not cooldown_expired:
            return False

        driver_labels = {
            -1: "No face detected",
            0: "Normal",
            1: "Drowsy",
        }

        road_labels = {
            0: "Normal road",
            1: "Pothole detected",
        }

        driver = driver_labels.get(int(driver_status), "Unknown")
        road = road_labels.get(int(road_status), "Unknown")

        if level == 2:
            title = "ROADGUARDIAN - HIGH RISK"
            priority = 5
            message = (
                "RoadGuardian predicted HIGH risk.\n"
                f"Driver input: {driver}\n"
                f"Road input: {road}\n"
                "Take precautions. Reduce speed and stop safely "
                "if the driver is drowsy."
            )
        else:
            title = "ROADGUARDIAN - MEDIUM RISK"
            priority = 4
            message = (
                "RoadGuardian predicted MEDIUM risk.\n"
                f"Driver input: {driver}\n"
                f"Road input: {road}\n"
                "Please remain alert and take appropriate precautions."
            )

        try:
            success = send_notification(
                title,
                message,
                priority=priority,
                tags="warning",
            )
        except Exception as exc:
            print("[RISK ALERT] Error:", exc)
            success = False

        self.last_level = level

        if success:
            self.last_sent_at = now
            print(f"[RISK ALERT] {title} sent to phone.")
        else:
            print(f"[RISK ALERT] {title} delivery failed.")

        return success
