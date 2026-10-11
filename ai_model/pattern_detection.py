
from pathlib import Path
import pandas as pd

# Find the dataset folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_FOLDER = PROJECT_ROOT / "ai_model" / "dataset"

INPUT_FILE = DATASET_FOLDER / "customer_category_spending.csv"
OUTPUT_FILE = DATASET_FOLDER / "customer_spending_patterns.csv"


def detect_patterns():

    # Read customer spending data
    df = pd.read_csv(INPUT_FILE)

    # Make sure numeric columns contain numbers
    df["transaction_count"] = pd.to_numeric(
        df["transaction_count"], errors="coerce"
    ).fillna(0)

    df["total_spending"] = pd.to_numeric(
        df["total_spending"], errors="coerce"
    ).fillna(0)

    patterns = []

    # Calculate the median spending for each category
    category_medians = df.groupby("category")[
        "total_spending"
    ].median()

    for _, row in df.iterrows():

        customer_id = int(row["customer_id"])
        category = row["category"]
        transaction_count = int(row["transaction_count"])
        total_spending = float(row["total_spending"])

        # Compare with other customers in the same category
        category_median = float(category_medians[category])

        high_spending = (
            total_spending >= category_median * 1.25
        )

        repeated_activity = transaction_count >= 2

        # Identify the spending pattern
        if high_spending and repeated_activity:
            pattern = "High and repeated spending"

        elif high_spending:
            pattern = "Higher-than-peer spending"

        elif repeated_activity:
            pattern = "Repeated spending activity"

        else:
            pattern = "Limited spending evidence"

        # Generate cautious green suggestions
        if category == "Energy":
            recommendation = (
                "Explore energy-efficient appliances, "
                "energy-saving practices, or renewable energy options."
            )

        elif category == "Transport":
            recommendation = (
                "Explore public transport, cycling, or shared mobility "
                "options where practical."
            )

        elif category == "Shopping":
            recommendation = (
                "Consider durable, reusable, and environmentally "
                "responsible products."
            )

        elif category == "Groceries":
            recommendation = (
                "Consider local products, reusable packaging, "
                "and reducing food waste."
            )

        elif category == "Housing":
            recommendation = (
                "More transaction history is needed before suggesting "
                "a specific housing-related green option."
            )

        else:
            recommendation = (
                "More information is needed for a suitable green suggestion."
            )

        # Store the detected pattern
        patterns.append({
            "customer_id": customer_id,
            "category": category,
            "transaction_count": transaction_count,
            "total_spending": total_spending,
            "category_median": category_median,
            "high_spending": high_spending,
            "repeated_activity": repeated_activity,
            "detected_pattern": pattern,
            "green_recommendation": recommendation
        })

    # Convert results into a DataFrame
    result = pd.DataFrame(patterns)

    # Save results
    result.to_csv(OUTPUT_FILE, index=False)

    print("\n========== SPENDING PATTERN ANALYSIS ==========\n")

    print(result[
        [
            "customer_id",
            "category",
            "total_spending",
            "detected_pattern"
        ]
    ].to_string(index=False))

    print("\n========== ANALYSIS COMPLETED ==========")
    print(f"\nTotal customer-category records: {len(result)}")
    print(f"High spending records: {result['high_spending'].sum()}")
    print(f"Repeated activity records: {result['repeated_activity'].sum()}")

    print("\nReport saved successfully!")
    print(f"Location: {OUTPUT_FILE}")


if __name__ == "__main__":
    detect_patterns()
