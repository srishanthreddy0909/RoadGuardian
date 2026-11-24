from integration.gps_alert_worker import GPSAlertWorker


def valid_fix(speed=0):
    return {
        "latitude": 17.4,
        "longitude": 78.5,
        "speed_kmh": speed,
    }


def safe_zone(lat, lon, verbose=False):
    return {
        "within_threshold": False,
        "risk_level": "HIGH",
        "location": "Test Zone",
        "distance_km": 5.0,
    }


def test_gps_lost_and_restored_notifications():
    sent = []
    worker = GPSAlertWorker(
        object(),
        gps_lost_after=15,
        notifier=lambda *a, **kw: sent.append((a, kw)) or True,
        zone_evaluator=safe_zone,
    )

    worker.process_no_fix(now=0)
    worker.process_no_fix(now=14)
    assert len(sent) == 0

    worker.process_no_fix(now=15)
    assert len(sent) == 1
    assert sent[0][0][0] == "ROADGUARDIAN - GPS LOST"

    worker.process_fix(valid_fix(), now=16)
    assert len(sent) == 2
    assert sent[1][0][0] == "ROADGUARDIAN - GPS RESTORED"


def test_geofence_alert_and_cooldown():
    sent = []

    def danger_zone(lat, lon, verbose=False):
        return {
            "within_threshold": True,
            "risk_level": "HIGH",
            "location": "Test Zone",
            "distance_km": 0.1,
        }

    worker = GPSAlertWorker(
        object(),
        notifier=lambda *a, **kw: sent.append((a, kw)) or True,
        zone_evaluator=danger_zone,
        zone_cooldown_seconds=300,
    )

    worker.process_fix(valid_fix(), now=100)
    worker.process_fix(valid_fix(), now=200)
    assert len(sent) == 1
    assert sent[0][0][0] == "ROADGUARDIAN - HIGH RISK"

    worker.process_fix(valid_fix(), now=401)
    assert len(sent) == 2


def test_no_geofence_alert_outside_threshold():
    sent = []
    worker = GPSAlertWorker(
        object(),
        notifier=lambda *a, **kw: sent.append(a) or True,
        zone_evaluator=safe_zone,
    )

    worker.process_fix(valid_fix(), now=100)
    assert sent == []


def test_overspeed_requires_five_seconds_and_has_hysteresis():
    sent = []
    worker = GPSAlertWorker(
        object(),
        speed_limit_kmh=40,
        overspeed_confirm_seconds=5,
        notifier=lambda *a, **kw: sent.append((a, kw)) or True,
        zone_evaluator=safe_zone,
    )

    worker.process_fix(valid_fix(45), now=0)
    worker.process_fix(valid_fix(45), now=4)
    assert len(sent) == 0

    worker.process_fix(valid_fix(45), now=5)
    assert len(sent) == 1
    assert sent[0][0][0] == "ROADGUARDIAN - OVERSPEED"

    worker.process_fix(valid_fix(45), now=8)
    assert len(sent) == 1

    worker.process_fix(valid_fix(30), now=9)
    worker.process_fix(valid_fix(45), now=10)
    worker.process_fix(valid_fix(45), now=15)
    assert len(sent) == 2


def test_failed_geofence_notification_is_retried():
    attempts = []

    def notifier(*args, **kwargs):
        attempts.append(args[0])
        return len(attempts) > 1

    def danger_zone(lat, lon, verbose=False):
        return {
            "within_threshold": True,
            "risk_level": "MEDIUM",
            "location": "Retry Zone",
            "distance_km": 0.2,
        }

    worker = GPSAlertWorker(
        object(),
        notifier=notifier,
        zone_evaluator=danger_zone,
    )

    worker.process_fix(valid_fix(), now=100)
    worker.process_fix(valid_fix(), now=102)

    assert len(attempts) == 2
