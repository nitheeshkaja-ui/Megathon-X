
from pathlib import Path
import pandas as pd

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_FOLDER = PROJECT_ROOT / "ai_model" / "dataset"

INPUT_FILE = DATASET_FOLDER / "customer_spending_patterns.csv"
OUTPUT_FILE = DATASET_FOLDER / "green_opportunities.csv"


def identify_opportunities():

    # Load detected customer spending patterns
    df = pd.read_csv(INPUT_FILE)

    opportunities = []

    def add_opportunity(customer_id, product, evidence, eligibility_note):
        opportunities.append({
            "customer_id": int(customer_id),
            "green_product": product,
            "spending_evidence": evidence,
            "eligibility_status": "Needs verification",
            "eligibility_note": eligibility_note
        })

    # Examine each customer's spending patterns
    for _, row in df.iterrows():

        customer_id = row["customer_id"]
        category = row["category"]
        total_spending = float(row["total_spending"])
        high_spending = str(row["high_spending"]).lower() == "true"

        # 1. Energy -> Solar Finance
        if category == "Energy" and high_spending:

            add_opportunity(
                customer_id,
                "Solar Finance",
                f"Higher-than-peer Energy spending: {total_spending}",
                "Verify roof suitability, local solar generation "
                "and financing eligibility."
            )

        # 2. Housing -> Green Home Loan
        elif category == "Housing" and high_spending:

            add_opportunity(
                customer_id,
                "Green Home Loan",
                f"Higher-than-peer Housing spending: {total_spending}",
                "Verify property details and eligibility for "
                "energy-efficient home improvements."
            )

        # 3. Transport -> EV Finance
        elif category == "Transport" and high_spending:

            add_opportunity(
                customer_id,
                "EV Finance",
                f"Higher-than-peer Transport spending: {total_spending}",
                "Transport spending does not prove vehicle ownership. "
                "Verify vehicle suitability and lender eligibility."
            )

    # 4. Go Paperless -> optional general offer
    # This is not inferred from spending behaviour.
    customer_ids = sorted(df["customer_id"].dropna().unique())

    for customer_id in customer_ids:

        add_opportunity(
            customer_id,
            "Go Paperless",
            "General optional digital banking offer; "
            "not based on spending behaviour.",
            "Check digital access and communication preferences."
        )

    # Create output report
    result = pd.DataFrame(opportunities)

    result.to_csv(OUTPUT_FILE, index=False)

    # Display results
    print("\n========== GREEN OPPORTUNITY REPORT ==========\n")

    if not result.empty:
        print(result.to_string(index=False))
    else:
        print("No potential opportunities identified.")

    print("\n========== SUMMARY ==========")

    print(f"Total opportunities: {len(result)}")

    if not result.empty:
        print("\nOpportunities by product:")
        print(result["green_product"].value_counts().to_string())

        print("\nUnique customers identified:")
        print(result["customer_id"].nunique())

    print("\nReport saved successfully!")
    print(f"Location: {OUTPUT_FILE}")


if __name__ == "__main__":
    identify_opportunities()
