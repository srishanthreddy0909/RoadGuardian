from gps_module.gps_reader import read_gps_fix
from gps_module.zone_detector import evaluate_zone


print("Waiting for GPS fix...")

try:
    fix = read_gps_fix(timeout=30)

    if fix is None:
        print("GPS UNAVAILABLE: No valid fix.")
        raise SystemExit(1)

    print("\nLIVE GPS POSITION")
    print(f"Latitude : {fix['latitude']:.6f}")
    print(f"Longitude: {fix['longitude']:.6f}")
    print(f"Satellites: {fix['satellites']}")
    print(f"HDOP: {fix['hdop']}")

    result = evaluate_zone(
        fix["latitude"],
        fix["longitude"]
    )

    print("\nACCIDENT ZONE RESULT")
    print("Nearest/relevant zone:", result["location"])
    print("Zone risk:", result["risk_level"])
    print(f"Distance: {result['distance_km']:.3f} km")
    print("GPS status:", result["gps_status"])

except (RuntimeError, ValueError, FileNotFoundError) as exc:
    print("GPS ZONE TEST ERROR:", exc)
    raise SystemExit(1)
