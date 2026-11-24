import RPi.GPIO as GPIO
import time

TRIG = 16
ECHO = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

ECHO_TIMEOUT = 0.03


def get_distance():
    """Return distance in cm, or None when no valid echo is received."""

    GPIO.output(TRIG, False)
    time.sleep(0.000002)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # Wait for the echo pulse to begin.
    wait_start = time.monotonic()

    while GPIO.input(ECHO) == 0:
        if time.monotonic() - wait_start > ECHO_TIMEOUT:
            return None

    pulse_start = time.monotonic()

    # Wait for the echo pulse to finish.
    while GPIO.input(ECHO) == 1:
        if time.monotonic() - pulse_start > ECHO_TIMEOUT:
            return None

    pulse_end = time.monotonic()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150

    return round(distance, 2)


if __name__ == "__main__":
    try:
        while True:
            distance = get_distance()

            if distance is None:
                print("No echo received - check sensor")
            else:
                print(f"Distance: {distance:.2f} cm")

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nStopping ultrasonic test...")

    finally:
        GPIO.cleanup()
