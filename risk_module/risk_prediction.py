import os
import joblib

# -----------------------------
# Load Model
# -----------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "risk_model.pkl")

model = joblib.load(MODEL_PATH)

print("Risk Model Loaded Successfully!")

# -----------------------------
# Risk Prediction Function
# -----------------------------

def predict_risk(driver_status, road_status, gps_status):

    prediction = model.predict(
        [[
            driver_status,
            road_status,
            gps_status
        ]]
    )[0]

    return int(prediction)


# -----------------------------
# Test Mode
# -----------------------------

if __name__ == "__main__":

    while True:

        print("\n==============================")

        driver = int(input("Driver Status (-1,0,1): "))
        road = int(input("Road Status (0,1): "))
        gps = int(input("GPS Status (0,1): "))

        risk = predict_risk(driver, road, gps)

        print("\nPrediction :", risk)

        if risk == 0:
            print("LOW RISK")

        elif risk == 1:
            print("MEDIUM RISK")

        else:
            print("HIGH RISK")

        choice = input("\nTest Again? (y/n): ")

        if choice.lower() != "y":
            break