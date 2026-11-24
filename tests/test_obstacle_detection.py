from sensor_module.obstacle_detection import (
    classify_distance,
    ObstacleAlertManager,
)


def test_distance_classification():
    assert classify_distance(None)["status"] == "UNAVAILABLE"
    assert classify_distance(100)["status"] == "CLEAR"
    assert classify_distance(20)["status"] == "WARNING"
    assert classify_distance(15)["status"] == "WARNING"
    assert classify_distance(10)["status"] == "CRITICAL"
    assert classify_distance(5)["status"] == "CRITICAL"


def test_invalid_distance_values():
    assert classify_distance(-1)["status"] == "INVALID"
    assert classify_distance("bad")["status"] == "INVALID"
    assert classify_distance(float("inf"))["status"] == "INVALID"


def test_obstacle_alert_and_cooldown():
    sent = []
    manager = ObstacleAlertManager(
        cooldown_seconds=60,
        notifier=lambda *a, **kw: sent.append((a, kw)) or True,
    )

    result = manager.process_distance(18, now=100)
    assert result["obstacle"] is True
    assert len(sent) == 1
    assert sent[0][0][0] == "ROADGUARDIAN - OBSTACLE WARNING"

    manager.process_distance(18, now=120)
    assert len(sent) == 1

    manager.process_distance(5, now=121)
    assert len(sent) == 2
    assert sent[1][0][0] == "ROADGUARDIAN - OBSTACLE CRITICAL"


def test_obstacle_alert_clears_with_hysteresis():
    sent = []
    manager = ObstacleAlertManager(
        notifier=lambda *a, **kw: sent.append(a) or True,
    )

    manager.process_distance(18, now=100)
    assert len(sent) == 1

    # 21 cm remains inside the 3 cm hysteresis margin.
    result = manager.process_distance(21, now=110)
    assert result["obstacle"] is True

    # A reading above 23 cm clears the active warning.
    result = manager.process_distance(24, now=120)
    assert result["obstacle"] is False

    manager.process_distance(18, now=130)
    assert len(sent) == 2


def test_unavailable_sensor_does_not_trigger_alert():
    sent = []
    manager = ObstacleAlertManager(
        notifier=lambda *a, **kw: sent.append(a) or True,
    )

    result = manager.process_distance(None, now=100)

    assert result["status"] == "UNAVAILABLE"
    assert result["obstacle"] is False
    assert sent == []


def test_failed_obstacle_notification_can_retry():
    attempts = []

    def notifier(*args, **kwargs):
        attempts.append(args[0])
        return len(attempts) > 1

    manager = ObstacleAlertManager(notifier=notifier)

    manager.process_distance(15, now=100)
    manager.process_distance(15, now=101)

    assert len(attempts) == 2
