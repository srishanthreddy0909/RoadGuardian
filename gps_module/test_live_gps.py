from gps_module.gps_reader import read_gps_fix

print("Waiting for a valid GPS fix...")

try:
    fix = read_gps_fix(timeout=30)

    if fix is None:
        print("NO VALID GPS FIX received within 30 seconds.")
    else:
        print("\nGPS FIX RECEIVED")
        print(f"Latitude    : {fix['latitude']:.6f}")
        print(f"Longitude   : {fix['longitude']:.6f}")
        print(f"Fix quality : {fix['fix_quality']}")
        print(f"Satellites  : {fix['satellites']}")
        print(f"HDOP        : {fix['hdop']}")
        print(f"UTC         : {fix['utc']}")

        if fix["hdop"] is not None and fix["hdop"] > 5:
            print("WARNING: GPS positioning accuracy may be poor.")

except RuntimeError as exc:
    print(f"GPS ERROR: {exc}")
