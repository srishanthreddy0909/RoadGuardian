"""Accident-zone detection using GPS coordinates."""

import csv
from pathlib import Path
from datetime import datetime

from gps_module.gps_engine import haversine
from gps_module.config import GPS_THRESHOLD, ENABLE_LOGS


CSV_PATH = Path(__file__).resolve().parent / "accident_zones.csv"

SEVERITY = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
}


def evaluate_zone(current_lat, current_lon, verbose=True):
    current_lat = float(current_lat)
    current_lon = float(current_lon)

    if not -90 <= current_lat <= 90:
        raise ValueError("Invalid latitude.")

    if not -180 <= current_lon <= 180:
        raise ValueError("Invalid longitude.")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    zones = []

    with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        required = {"Location", "Latitude", "Longitude", "RiskLevel"}

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Accident-zone CSV has missing columns.")

        for row in reader:
            risk_level = row["RiskLevel"].strip().upper()

            if risk_level not in SEVERITY:
                raise ValueError(f"Unknown risk level: {risk_level}")

            distance = haversine(
                current_lat,
                current_lon,
                float(row["Latitude"]),
                float(row["Longitude"]),
            )

            zones.append({
                "location": row["Location"],
                "risk_level": risk_level,
                "distance_km": distance,
                "severity": SEVERITY[risk_level],
            })

    if not zones:
        raise ValueError("No accident zones found in CSV.")

    nearby = [
        zone for zone in zones
        if zone["distance_km"] <= GPS_THRESHOLD
    ]

    if nearby:
        selected = max(
            nearby,
            key=lambda zone: (zone["severity"], -zone["distance_km"]),
        )
        within_threshold = True
    else:
        selected = min(zones, key=lambda zone: zone["distance_km"])
        within_threshold = False

    gps_status = int(
        within_threshold
        and selected["severity"] >= SEVERITY["MEDIUM"]
    )

    result = {
        "gps_status": gps_status,
        "location": selected["location"],
        "risk_level": selected["risk_level"],
        "distance_km": selected["distance_km"],
        "within_threshold": within_threshold,
        "threshold_km": GPS_THRESHOLD,
    }

    if verbose:
        if ENABLE_LOGS:
            print("\n--- GPS ZONE DEBUG ---")
            print("Time:", datetime.now())
            print(f"Position: {current_lat:.6f}, {current_lon:.6f}")
            print("Zone:", selected["location"])
            print("Risk:", selected["risk_level"])
            print(f"Distance: {selected['distance_km']:.3f} km")
            print("GPS status:", gps_status)

        if gps_status:
            print(f"{selected['risk_level']} RISK ACCIDENT ZONE ALERT")
        elif within_threshold:
            print("LOW RISK ZONE WARNING")
        else:
            print("SAFE ZONE")

    return result


def detect_zone(current_lat, current_lon):
    return evaluate_zone(current_lat, current_lon)["gps_status"]
