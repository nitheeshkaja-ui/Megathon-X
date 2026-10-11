
import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv


# --------------------------------------------------
# 1. DATABASE CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"

load_dotenv(ENV_FILE)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "green_customer_insights"),
}


# --------------------------------------------------
# 2. RETRIEVE TRANSACTIONS FROM MYSQL
# --------------------------------------------------

def get_transactions():
    connection = None

    try:
        print("Connecting to MySQL...")

        connection = mysql.connector.connect(**DB_CONFIG)

        query = """
            SELECT
                c.customer_id,
                t.transaction_id,
                t.category,
                t.amount,
                t.transaction_type,
                t.transaction_date,
                t.description
            FROM transactions t
            JOIN accounts a
                ON t.account_id = a.account_id
            JOIN customers c
                ON a.customer_id = c.customer_id
            ORDER BY c.customer_id, t.transaction_date;
        """

        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)

        records = cursor.fetchall()
        cursor.close()

        df = pd.DataFrame(records)

        print("Database connection successful!")
        print("Total transactions retrieved:", len(df))

        return df

    except mysql.connector.Error as error:
        print("Database error:", error)
        return pd.DataFrame()

    finally:
        if connection and connection.is_connected():
            connection.close()
            print("Database connection closed.")


# --------------------------------------------------
# 3. CUSTOMER SPENDING ANALYSIS
# --------------------------------------------------

def analyze_spending(df):

    if df.empty:
        print("No transaction data available.")
        return

    # Only debit transactions represent outgoing payments
    debit_df = df[
        df["transaction_type"] == "Debit"
    ].copy()

    debit_df["amount"] = pd.to_numeric(
        debit_df["amount"], errors="coerce"
    )

    debit_df = debit_df.dropna(subset=["amount"])

    print("\n========== SPENDING ANALYSIS ==========")

    print("\nTotal debit transactions:", len(debit_df))

    # Category-wise spending across all customers
    category_summary = (
        debit_df.groupby("category")
        .agg(
            transaction_count=("transaction_id", "count"),
            total_spending=("amount", "sum"),
            average_spending=("amount", "mean")
        )
        .reset_index()
    )

    category_summary["total_spending"] = (
        category_summary["total_spending"].round(2)
    )

    category_summary["average_spending"] = (
        category_summary["average_spending"].round(2)
    )

    print("\nCATEGORY-WISE SPENDING:")
    print(category_summary.to_string(index=False))

    # Spending by each customer and category
    customer_category = (
        debit_df.groupby(["customer_id", "category"])
        .agg(
            transaction_count=("transaction_id", "count"),
            total_spending=("amount", "sum"),
            average_spending=("amount", "mean")
        )
        .reset_index()
    )

    # Total debit spending per customer
    customer_totals = (
        debit_df.groupby("customer_id")
        .agg(
            total_transactions=("transaction_id", "count"),
            total_spending=("amount", "sum")
        )
        .reset_index()
    )

    # Find each customer's highest-spending category
    highest_category = (
        customer_category.loc[
            customer_category.groupby("customer_id")[
                "total_spending"
            ].idxmax()
        ][["customer_id", "category", "total_spending"]]
        .rename(columns={
            "category": "highest_spending_category",
            "total_spending": "highest_category_amount"
        })
    )

    customer_summary = customer_totals.merge(
        highest_category,
        on="customer_id",
        how="left"
    )

    print("\nCUSTOMER-WISE SPENDING:")
    print(customer_summary.to_string(index=False))

    # Save reports
    output_folder = PROJECT_ROOT / "ai_model" / "dataset"
    output_folder.mkdir(parents=True, exist_ok=True)

    category_summary.to_csv(
        output_folder / "category_spending_summary.csv",
        index=False
    )

    customer_summary.to_csv(
        output_folder / "customer_spending_summary.csv",
        index=False
    )

    customer_category.to_csv(
        output_folder / "customer_category_spending.csv",
        index=False
    )

    print("\nReports saved successfully!")
    print("Location:", output_folder)


# --------------------------------------------------
# 4. MAIN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":

    transactions = get_transactions()

    if not transactions.empty:
        analyze_spending(transactions)
