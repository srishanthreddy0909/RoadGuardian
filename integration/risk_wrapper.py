import os
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "risk_module", "risk_model.pkl")

model = joblib.load(MODEL_PATH)

def predict_risk(driver_status, road_status, gps_status):

    prediction = model.predict(
        [[
            driver_status,
            road_status,
            gps_status
        ]]
    )[0]

    return int(prediction)