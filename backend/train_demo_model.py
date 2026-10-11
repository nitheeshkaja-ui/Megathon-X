
import pandas as pd
import numpy as np
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# 1. Load the customer feature dataset
df = pd.read_csv("customer_features.csv")

# 2. Select features available in our dataset
feature_columns = [
    "city",
    "digital_banking",
    "paper_statement",
    "home_owner",
    "solar_interest",
    "vehicle_type",
    "account_count",
    "transaction_count",
    "total_debit_amount",
    "total_credit_amount",
    "average_transaction_amount",
    "energy_spending",
    "transport_spending",
    "travel_spending",
]

X = df[feature_columns].copy()

# 3. Create synthetic demonstration labels.
# These are NOT actual customer purchase outcomes.
rng = np.random.default_rng(42)

synthetic_score = (
    1.5 * df["solar_interest"].fillna(0)
    + 0.8 * df["home_owner"].fillna(0)
    + 0.6 * (df["vehicle_type"] == "Electric").astype(int)
    + 0.4 * df["digital_banking"].fillna(0)
    - 0.5 * df["paper_statement"].fillna(0)
    + rng.normal(0, 0.5, size=len(df))
)

# Synthetic labels for demonstration only
y = (synthetic_score >= synthetic_score.median()).astype(int)

if y.nunique() < 2 or y.value_counts().min() < 2:
    raise ValueError(
        "Need at least two examples in each synthetic class."
    )

# 4. Identify numeric and categorical features
numeric_features = [
    "digital_banking",
    "paper_statement",
    "home_owner",
    "solar_interest",
    "account_count",
    "transaction_count",
    "total_debit_amount",
    "total_credit_amount",
    "average_transaction_amount",
    "energy_spending",
    "transport_spending",
    "travel_spending",
]

categorical_features = ["city", "vehicle_type"]

numeric_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore")),
])

preprocessor = ColumnTransformer([
    ("numeric", numeric_pipeline, numeric_features),
    ("categorical", categorical_pipeline, categorical_features),
])

# 5. Split data for a demonstration evaluation
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y,
)

# 6. Build and train the model
model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )),
])

model.fit(X_train, y_train)

# 7. Evaluate on held-out synthetic examples
predictions = model.predict(X_test)

print("GIFT2 DEMONSTRATION MODEL")
print("Training labels: SYNTHETIC")
print("Customers:", len(df))
print("Training rows:", len(X_train))
print("Test rows:", len(X_test))
print("Synthetic-label test accuracy:",
      round(accuracy_score(y_test, predictions), 3))
print("\nClassification report:")
print(classification_report(
    y_test,
    predictions,
    zero_division=0,
))

# 8. Save the model and its metadata
joblib.dump(
    {
        "model": model,
        "feature_columns": feature_columns,
        "model_version": "synthetic-demo-v1",
        "training_label_source": "synthetic",
        "warning": (
            "Not validated for real customer purchase propensity."
        ),
    },
    "gift2_demo_model.joblib",
)

print("\nSaved: gift2_demo_model.joblib")
print("This model is for demonstration only.")
