from integration.driver_wrapper import convert_driver_status
from integration.road_wrapper import convert_road_status
from integration.gps_wrapper import convert_gps_status
from integration.risk_wrapper import predict_risk

from gps_module.gps_monitor import GPSMonitor
from gps_module.zone_detector import evaluate_zone
from integration.gps_alert_worker import GPSAlertWorker
from integration.risk_alerts import RiskAlertManager

from sensor_module.ultrasonic import get_distance
from sensor_module.obstacle_detection import ObstacleAlertManager

import RPi.GPIO as GPIO
import time


# GPS monitoring
gps_monitor = GPSMonitor(
    port="/dev/serial0",
    baudrate=9600,
    stale_after=5,
    min_satellites=3,
    max_hdop=10.0,
)

# Automatic phone alerts
alert_worker = GPSAlertWorker(
    gps_monitor,
    speed_limit_kmh=40.0,
)

risk_alerts = RiskAlertManager(cooldown_seconds=300)
obstacle_alerts = ObstacleAlertManager(cooldown_seconds=60)


def main():
    print("===================================")
    print(" RoadGuardian Risk Prediction")
    print("===================================")
    print("Starting live GPS monitor...")

    gps_monitor.start()
    alert_worker.start()

    try:
        while True:
            print("\nDriver Status")
            print("-1 = No Face")
            print(" 0 = Normal")
            print(" 1 = Drowsy")

            driver_status = int(input("Enter Driver Status: "))

            if driver_status not in (-1, 0, 1):
                print("Invalid driver status.")
                continue

            print("\nRoad Status")
            print("0 = Normal Road")
            print("1 = Pothole")

            road_status = int(input("Enter Road Status: "))

            if road_status not in (0, 1):
                print("Invalid road status.")
                continue

            # Read ultrasonic sensor independently.
            distance = get_distance()
            obstacle_result = obstacle_alerts.process_distance(distance)

            driver = convert_driver_status(driver_status)
            road = convert_road_status(road_status)

            # Read latest GPS fix.
            fix = gps_monitor.get_fix()

            gps_text = "UNAVAILABLE"
            risk_text = "NOT CALCULATED"
            gps_status = None
            zone_result = None
            risk = None

            if fix is not None:
                try:
                    zone_result = evaluate_zone(
                        fix["latitude"],
                        fix["longitude"],
                    )

                    gps_status = convert_gps_status(
                        zone_result["gps_status"]
                    )

                    gps_text = "VALID"

                    risk = predict_risk(
                        driver,
                        road,
                        gps_status,
                    )

                    risk_text = {
                        0: "SAFE",
                        1: "MEDIUM",
                        2: "HIGH",
                    }.get(int(risk), "UNKNOWN")

                    risk_alerts.notify_if_needed(
                        risk,
                        driver_status=driver_status,
                        road_status=road_status,
                    )

                except Exception as exc:
                    print("GPS/Risk processing error:", repr(exc))
                    gps_text = "UNAVAILABLE"
                    risk_text = "NOT CALCULATED"

            else:
                print("\nGPS UNAVAILABLE")
                gps_error = gps_monitor.get_error()

                if gps_error:
                    print("GPS error:", gps_error)

                print(
                    "Risk prediction skipped: "
                    "GPS fix is missing, weak, or stale."
                )

            obstacle_detected = obstacle_result["obstacle"]

            if obstacle_detected:
                print("\n*** OBSTACLE DETECTED ***")

            print("\n=================================")
            print("Driver   :", driver_status)
            print("Road     :", road_status)
            print("GPS      :", gps_text)

            if fix is not None and gps_text == "VALID":
                print(
                    "Position :",
                    f"{fix['latitude']:.6f}, "
                    f"{fix['longitude']:.6f}",
                )
                print("Satellites:", fix["satellites"])
                print("HDOP     :", fix["hdop"])
                print("Speed    :", fix.get("speed_kmh"), "km/h")
                print("GPS Zone :", zone_result["location"])
                print("Zone Risk:", zone_result["risk_level"])
                print(
                    "Zone Distance:",
                    f"{zone_result['distance_km']:.3f} km",
                )

            if distance is None:
                print("Distance : SENSOR UNAVAILABLE")
            else:
                print("Distance :", round(distance, 2), "cm")

            print("Risk     :", risk_text)
            print("Obstacle :", "YES" if obstacle_detected else "NO")
            print("Sensor state:", obstacle_result["status"])
            print("=================================")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopping RoadGuardian...")

    finally:
        alert_worker.stop()
        gps_monitor.stop()
        GPIO.cleanup()
        print("GPIO cleaned up. System stopped.")


if __name__ == "__main__":
    main()
