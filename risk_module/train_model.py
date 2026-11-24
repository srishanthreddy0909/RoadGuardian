"""Train the RoadGuardian risk model without requiring pandas."""

import csv
from pathlib import Path

import joblib
import sklearn

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset" / "RoadGuardian_Risk_Dataset.csv"
MODEL_PATH = BASE_DIR / "risk_model.pkl"

FEATURES = ["driver_status", "road_status", "gps_status"]
TARGET = "risk_level"

X = []
y = []

with DATASET_PATH.open("r", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    required = FEATURES + [TARGET]

    if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
        raise ValueError("Dataset is missing required columns.")

    for row in reader:
        X.append([int(row[name]) for name in FEATURES])
        y.append(int(row[TARGET]))

if not X:
    raise ValueError("Dataset is empty.")

if set(y) != {0, 1, 2}:
    raise ValueError(f"Expected risk classes 0, 1, 2; found {set(y)}")

combinations = {}
for features, label in zip(X, y):
    key = tuple(features)
    if key in combinations and combinations[key] != label:
        raise ValueError(f"Conflicting label for input {key}")
    combinations[key] = label

print("Dataset records:", len(X))
print("Unique input combinations:", len(combinations))
print("Conflicting labels: 0")
print("Scikit-learn version:", sklearn.__version__)

# Random-row evaluation is retained for comparison with the old script.
# Because combinations are repeated, this is not an independent
# real-world generalisation test.
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

evaluation_model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
)
evaluation_model.fit(X_train, y_train)

predictions = evaluation_model.predict(X_test)

print(
    "Random-row test accuracy:",
    round(accuracy_score(y_test, predictions) * 100, 2),
    "%",
)
print("Note: repeated input combinations make this score optimistic.")

# Train the deployment model on the complete dataset.
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
)
model.fit(X, y)

joblib.dump(model, MODEL_PATH)

print("\nFinal model saved:", MODEL_PATH)
print("Model classes:", model.classes_)
print("Input features:", len(FEATURES))
print("Feature order:", FEATURES)
