
import os
import re
import secrets
import threading

import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app)

# Demo-only OTP storage. OTPs are not sent by SMS.
OTP_STORE = {}
OTP_LOCK = threading.Lock()


# ---------------- DATABASE ----------------

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "green_customer_insights"),
    )


def close_db(cursor, connection):
    if cursor:
        cursor.close()

    if connection and connection.is_connected():
        connection.close()


# ---------------- HELPERS ----------------

def get_data():
    return request.get_json(silent=True) or {}


def error_response(message, status=400):
    return jsonify({
        "success": False,
        "message": message
    }), status


def normalize_phone(value):
    phone = re.sub(r"[\s-]", "", str(value or ""))

    if not re.fullmatch(r"\+?\d{7,15}", phone):
        return None

    return phone


# ---------------- HOME AND HEALTH ----------------

@app.route("/")
def home():
    return jsonify({
        "message": "Green Customer Insights Platform API is running"
    })


@app.route("/api/health")
def health():
    connection = None

    try:
        connection = get_db_connection()

        return jsonify({
            "backend": "running",
            "database": "connected"
        })

    except mysql.connector.Error:
        app.logger.exception("Health check failed")

        return jsonify({
            "backend": "running",
            "database": "disconnected"
        }), 500

    finally:
        if connection and connection.is_connected():
            connection.close()


# ---------------- BRANCHES ----------------

@app.route("/api/branches")
def get_branches():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                br.branch_id,
                br.branch_name,
                br.city,
                br.area,
                b.bank_id,
                b.bank_name
            FROM branches br
            JOIN banks b ON b.bank_id = br.bank_id
            WHERE b.is_active = 1
            ORDER BY b.bank_name, br.branch_name
        """)

        return jsonify(cursor.fetchall())

    except mysql.connector.Error:
        app.logger.exception("Branch query failed")
        return error_response("Unable to load branches.", 500)

    finally:
        close_db(cursor, connection)


# ---------------- DEMO OTP ----------------

@app.route("/api/auth/send-demo-otp", methods=["POST"])
def send_demo_otp():
    data = get_data()
    phone = normalize_phone(data.get("phone_number"))

    if not phone:
        return error_response("Enter a valid phone number.")

    otp = f"{secrets.randbelow(1000000):06d}"

    with OTP_LOCK:
        OTP_STORE[phone] = otp

    return jsonify({
        "success": True,
        "message": "Demo OTP generated. No SMS was sent.",
        "demo_otp": otp
    })


# ---------------- CUSTOMER REGISTRATION ----------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = get_data()

    full_name = str(data.get("full_name", "")).strip()
    phone = normalize_phone(data.get("phone_number"))
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))
    otp = str(data.get("otp", "")).strip()
    city = str(data.get("city", "")).strip()
    customer_ref = str(data.get("customer_ref", "")).strip()
    account_number = str(data.get("account_number", "")).strip()

    try:
        branch_id = int(data.get("branch_id"))
    except (TypeError, ValueError):
        return error_response("Select a valid branch.")

    if not full_name or len(full_name) > 120:
        return error_response("Enter your full name.")

    if not phone:
        return error_response("Enter a valid phone number.")

    if len(email) > 150 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        return error_response("Enter a valid email address.")

    if len(password) < 8:
        return error_response(
            "Password must contain at least 8 characters."
        )

    if password != confirm_password:
        return error_response("Passwords do not match.")

    if not otp:
        return error_response("Enter the demo OTP.")

    if bool(customer_ref) != bool(account_number):
        return error_response(
            "Enter both customer reference and account number "
            "to link an account."
        )

    with OTP_LOCK:
        expected_otp = OTP_STORE.get(phone)

        if not expected_otp or not secrets.compare_digest(
            otp, expected_otp
        ):
            return error_response(
                "Invalid OTP. Generate a new demo OTP."
            )

        del OTP_STORE[phone]

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT branch_id, bank_id, city
            FROM branches
            WHERE branch_id = %s
        """, (branch_id,))

        branch = cursor.fetchone()

        if not branch:
            connection.rollback()
            return error_response("Selected branch was not found.")

        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE username = %s OR email = %s
            LIMIT 1
        """, (phone, email))

        if cursor.fetchone():
            connection.rollback()
            return error_response(
                "This phone number or email is already registered.",
                409
            )

        if account_number:
            cursor.execute("""
                SELECT
                    a.account_id,
                    a.account_status,
                    a.bank_id,
                    a.branch_id,
                    c.customer_id,
                    c.customer_ref,
                    c.full_name,
                    c.email,
                    c.phone_number
                FROM accounts a
                JOIN customers c ON c.customer_id = a.customer_id
                WHERE a.account_number = %s
                  AND c.customer_ref = %s
                FOR UPDATE
            """, (account_number, customer_ref))

            linked = cursor.fetchone()

            if not linked or linked["account_status"] != "Active":
                connection.rollback()
                return error_response(
                    "Account details could not be verified."
                )

            saved_phone = linked.get("phone_number")

            if saved_phone and saved_phone != phone:
                connection.rollback()
                return error_response(
                    "This customer profile has a different phone number."
                )

            saved_email = linked.get("email")

            if saved_email and saved_email.lower() != email:
                connection.rollback()
                return error_response(
                    "Use the email address associated with this profile."
                )

            customer_id = linked["customer_id"]
            bank_id = linked["bank_id"]
            chosen_branch_id = linked["branch_id"] or branch_id

            cursor.execute("""
                UPDATE customers
                SET phone_number = %s,
                    email = COALESCE(email, %s)
                WHERE customer_id = %s
            """, (phone, email, customer_id))

        else:
            cursor.execute("""
                SELECT customer_id
                FROM customers
                WHERE phone_number = %s OR email = %s
                LIMIT 1
            """, (phone, email))

            if cursor.fetchone():
                connection.rollback()
                return error_response(
                    "A customer profile already exists. "
                    "If you have a bank account, use account linking.",
                    409
                )

            new_customer_ref = "CUST-" + secrets.token_hex(8).upper()

            cursor.execute("""
                INSERT INTO customers
                    (customer_ref, full_name, email, phone_number, city)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                new_customer_ref,
                full_name,
                email,
                phone,
                city or branch["city"]
            ))

            customer_id = cursor.lastrowid
            bank_id = branch["bank_id"]
            chosen_branch_id = branch_id

        cursor.execute("""
            INSERT INTO users
                (username, password_hash, role_id, customer_id, bank_id,
                 branch_id, full_name, email, is_active)
            VALUES (%s, %s, 1, %s, %s, %s, %s, %s, 1)
        """, (
            phone,
            generate_password_hash(password),
            customer_id,
            bank_id,
            chosen_branch_id,
            full_name,
            email
        ))

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful.",
            "user": {
                "user_id": user_id,
                "customer_id": customer_id,
                "full_name": full_name,
                "phone_number": phone,
                "email": email,
                "role": "Customer",
                "bank_id": bank_id,
                "branch_id": chosen_branch_id
            }
        }), 201

    except mysql.connector.IntegrityError:
        if connection:
            connection.rollback()

        return error_response(
            "A matching record already exists. Check your phone and email.",
            409
        )

    except mysql.connector.Error:
        if connection:
            connection.rollback()

        app.logger.exception("Registration database error")

        return error_response(
            "Registration failed due to a database error.", 500
        )

    finally:
        close_db(cursor, connection)


# ---------------- LOGIN ----------------

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = get_data()

    identifier = str(
        data.get("phone_number")
        or data.get("email")
        or data.get("username")
        or ""
    ).strip()

    password = str(data.get("password", ""))

    if not identifier or not password:
        return error_response(
            "Enter your phone number or email and password."
        )

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                u.user_id,
                u.username,
                u.password_hash,
                u.full_name,
                u.email,
                u.role_id,
                u.customer_id,
                u.bank_id,
                u.branch_id,
                u.is_active,
                r.role_name
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            WHERE u.username = %s OR u.email = %s
            LIMIT 1
        """, (identifier, identifier))

        user = cursor.fetchone()

        if (
            not user
            or not user["is_active"]
            or not check_password_hash(
                user["password_hash"], password
            )
        ):
            return error_response(
                "Invalid phone number/email or password.", 401
            )

        if user["role_id"] != 1:
            return error_response(
                "Please use the sign-in page for your account type.",
                403
            )

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "user": {
                "user_id": user["user_id"],
                "customer_id": user["customer_id"],
                "full_name": user["full_name"],
                "phone_number": user["username"],
                "email": user["email"],
                "role": user["role_name"],
                "bank_id": user["bank_id"],
                "branch_id": user["branch_id"]
            }
        })

    except mysql.connector.Error:
        app.logger.exception("Login database error")

        return error_response(
            "Login failed due to a database error.", 500
        )

    finally:
        close_db(cursor, connection)


# ---------------- DASHBOARD SUMMARY ----------------

@app.route("/api/dashboard/summary")
def dashboard_summary():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM banks) AS total_banks,
                (SELECT COUNT(*) FROM customers) AS total_customers,
                (SELECT COUNT(*) FROM accounts) AS total_accounts,
                (SELECT COUNT(*) FROM transactions) AS total_transactions
        """)

        return jsonify(cursor.fetchone())

    except mysql.connector.Error:
        app.logger.exception("Dashboard summary failed")

        return error_response(
            "Unable to load dashboard summary.", 500
        )

    finally:
        close_db(cursor, connection)


# ---------------- BANKS ----------------

@app.route("/api/banks")
def get_banks():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                b.bank_id,
                b.bank_name,
                COUNT(DISTINCT c.customer_id) AS customer_count,
                COUNT(DISTINCT t.transaction_id) AS transaction_count
            FROM banks b
            LEFT JOIN accounts a ON a.bank_id = b.bank_id
            LEFT JOIN customers c ON c.customer_id = a.customer_id
            LEFT JOIN transactions t ON t.account_id = a.account_id
            GROUP BY b.bank_id, b.bank_name
            ORDER BY b.bank_id
        """)

        return jsonify(cursor.fetchall())

    except mysql.connector.Error:
        app.logger.exception("Banks query failed")

        return error_response(
            "Unable to load banks.", 500
        )

    finally:
        close_db(cursor, connection)


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
