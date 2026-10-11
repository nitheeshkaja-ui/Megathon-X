
from pathlib import Path
import json
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import os

# --------------------------------
# 1. PROJECT PATHS
# --------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / "backend" / ".env"

CSV_FILE = (
    PROJECT_ROOT
    / "ai_model"
    / "dataset"
    / "green_opportunities.csv"
)

load_dotenv(ENV_FILE)

# --------------------------------
# 2. DATABASE CONFIGURATION
# --------------------------------

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv(
        "DB_NAME",
        "green_customer_insights"
    )
}

# --------------------------------
# 3. GREEN PRODUCT IDs
# --------------------------------

PRODUCT_IDS = {
    "EV Finance": 1,
    "Green Home Loan": 2,
    "Solar Finance": 3,
    "Go Paperless": 4
}

MODEL_VERSION = "rules-v1"


def save_recommendations():

    connection = None
    cursor = None

    try:

        # --------------------------------
        # 4. READ CSV
        # --------------------------------

        df = pd.read_csv(CSV_FILE)

        print("\nCSV loaded successfully!")
        print("Total opportunities:", len(df))

        # --------------------------------
        # 5. CONNECT TO MYSQL
        # --------------------------------

        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        print("MySQL connected successfully!")

        inserted = 0
        skipped = 0

        # --------------------------------
        # 6. PROCESS EACH OPPORTUNITY
        # --------------------------------

        for _, row in df.iterrows():

            customer_id = int(row["customer_id"])
            product_name = row["green_product"]

            # Find product ID
            product_id = PRODUCT_IDS.get(product_name)

            if product_id is None:
                print("Unknown product:", product_name)
                skipped += 1
                continue

            # Check whether this customer-product
            # recommendation already exists
            cursor.execute(
                """
                SELECT recommendation_id
                FROM recommendations
                WHERE customer_id = %s
                  AND product_id = %s
                LIMIT 1
                """,
                (customer_id, product_id)
            )

            existing = cursor.fetchone()

            if existing:
                print(
                    f"Skipped duplicate: Customer {customer_id}, "
                    f"{product_name}"
                )
                skipped += 1
                continue

            # --------------------------------
            # 7. PREPARE EVIDENCE
            # --------------------------------

            evidence = {
                "spending_evidence": str(
                    row["spending_evidence"]
                ),
                "eligibility_status": str(
                    row["eligibility_status"]
                ),
                "eligibility_note": str(
                    row["eligibility_note"]
                )
            }

            reason_codes = [
                "RULE_BASED_OPPORTUNITY",
                product_name.upper().replace(" ", "_")
            ]

            explanation = (
                f"{product_name} was identified as a potential "
                f"opportunity for customer {customer_id}. "
                f"Evidence: {row['spending_evidence']}. "
                f"This is not an eligibility approval. "
                f"{row['eligibility_note']}"
            )

            # --------------------------------
            # 8. INSERT INTO MYSQL
            # --------------------------------

            insert_query = """
                INSERT INTO recommendations (
                    customer_id,
                    product_id,
                    propensity_score,
                    model_version,
                    reason_codes,
                    evidence_snapshot,
                    ai_explanation,
                    recommendation_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                customer_id,
                product_id,
                None,
                MODEL_VERSION,
                json.dumps(reason_codes),
                json.dumps(evidence),
                explanation,
                "Recommended"
            )

            cursor.execute(insert_query, values)

            inserted += 1

            print(
                f"Inserted: Customer {customer_id} - "
                f"{product_name}"
            )

        # --------------------------------
        # 9. COMMIT TRANSACTION
        # --------------------------------

        connection.commit()

        print("\n========== DATABASE SUMMARY ==========")
        print("New recommendations inserted:", inserted)
        print("Records skipped:", skipped)
        print("Model version:", MODEL_VERSION)
        print("\nRecommendations saved successfully!")

    except Exception as error:

        if connection and connection.is_connected():
            connection.rollback()

        print("\nERROR:", error)
        print("Database changes rolled back.")

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

        print("\nDatabase connection closed.")


if __name__ == "__main__":
    save_recommendations()
