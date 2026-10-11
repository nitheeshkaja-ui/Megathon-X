
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()


def build_customer_features():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv(
            "DB_NAME",
            "green_customer_insights"
        ),
    )

    try:
        query = """
        SELECT
            c.customer_id,
            c.city,
            c.digital_banking,
            c.paper_statement,
            c.home_owner,
            c.solar_interest,
            c.vehicle_type,

            COUNT(DISTINCT a.account_id) AS account_count,

            COUNT(t.transaction_id) AS transaction_count,

            COALESCE(SUM(
                CASE
                    WHEN t.transaction_type = 'Debit'
                    THEN t.amount ELSE 0
                END
            ), 0) AS total_debit_amount,

            COALESCE(SUM(
                CASE
                    WHEN t.transaction_type = 'Credit'
                    THEN t.amount ELSE 0
                END
            ), 0) AS total_credit_amount,

            COALESCE(AVG(t.amount), 0)
                AS average_transaction_amount,

            COALESCE(SUM(
                CASE WHEN t.category = 'Energy'
                    AND t.transaction_type = 'Debit'
                    THEN t.amount ELSE 0 END
            ), 0) AS energy_spending,

            COALESCE(SUM(
                CASE WHEN t.category = 'Transport'
                    AND t.transaction_type = 'Debit'
                    THEN t.amount ELSE 0 END
            ), 0) AS transport_spending,

            COALESCE(SUM(
                CASE WHEN t.category = 'Travel'
                    AND t.transaction_type = 'Debit'
                    THEN t.amount ELSE 0 END
            ), 0) AS travel_spending

        FROM customers c

        LEFT JOIN accounts a
            ON c.customer_id = a.customer_id

        LEFT JOIN transactions t
            ON a.account_id = t.account_id

        GROUP BY
            c.customer_id,
            c.city,
            c.digital_banking,
            c.paper_statement,
            c.home_owner,
            c.solar_interest,
            c.vehicle_type

        ORDER BY c.customer_id;
        """

        features = pd.read_sql_query(query, connection)

        print("\nCustomer feature dataset created.")
        print("Rows:", len(features))
        print("Columns:", len(features.columns))
        print("\nPreview:")
        print(features.head().to_string(index=False))

        output_file = "customer_features.csv"
        features.to_csv(output_file, index=False)

        print(f"\nSaved dataset to: {output_file}")

        return features

    finally:
        connection.close()


if __name__ == "__main__":
    build_customer_features()
