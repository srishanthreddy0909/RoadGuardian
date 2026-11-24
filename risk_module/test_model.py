import joblib

# ------------------------
# LOAD MODEL
# ------------------------

model = joblib.load("risk_model.pkl")

print("\nModel Loaded Successfully!\n")

# ------------------------
# TAKE INPUTS
# ------------------------

driver_status = int(input("Enter Driver Status (-1,0,1): "))

road_status = int(input("Enter Road Status (0,1): "))

gps_status = int(input("Enter GPS Status (0,1): "))

# ------------------------
# PREDICT
# ------------------------

prediction = model.predict(

    [[

        driver_status,

        road_status,

        gps_status

    ]]

)[0]

# ------------------------
# DISPLAY RESULT
# ------------------------

if prediction == 0:

    print("\nLOW RISK")

elif prediction == 1:

    print("\nMEDIUM RISK")

else:

    print("\nHIGH RISK")