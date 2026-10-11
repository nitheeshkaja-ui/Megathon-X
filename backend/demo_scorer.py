
import pandas as pd
import numpy as np

df = pd.read_csv("customer_features.csv")

# Demonstration rules only; not trained ML.
scores = pd.DataFrame({
    "customer_id": df["customer_id"],
    "solar_finance_score": (
        0.50 * df["solar_interest"].fillna(0)
        + 0.30 * df["home_owner"].fillna(0)
        + 0.20 * (
            df["energy_spending"].fillna(0)
            / max(df["energy_spending"].max(), 1)
        )
    ),
    "ev_finance_score": (
        0.60 * df["vehicle_type"].isin(
            ["Electric", "Hybrid"]
        ).astype(float)
        + 0.40 * (
            df["transport_spending"].fillna(0)
            / max(df["transport_spending"].max(), 1)
        )
    ),
    "green_home_loan_score": (
        0.60 * df["home_owner"].fillna(0)
        + 0.40 * (
            df["energy_spending"].fillna(0)
            / max(df["energy_spending"].max(), 1)
        )
    ),
    "go_paperless_score": (
        0.70 * df["digital_banking"].fillna(0)
        + 0.30 * (
            1 - df["paper_statement"].fillna(1)
        )
    ),
})

print("GIFT2 RULE-BASED DEMONSTRATION")
print("These scores are not purchase probabilities.")
print(scores.head(10).to_string(index=False))

scores.to_csv("demo_recommendation_scores.csv", index=False)
print("\nSaved demo_recommendation_scores.csv")
