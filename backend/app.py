import os
import csv

import re

import secrets

import threading



import mysql.connector

from flask import Flask, jsonify, request

from flask_cors import CORS

from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash





# =========================================================

# CONFIGURATION

# =========================================================



load_dotenv(

    os.path.join(os.path.dirname(__file__), ".env")

)



app = Flask(__name__)

CORS(app)



# Demo-only OTP storage. No SMS is sent.

OTP_STORE = {}

OTP_LOCK = threading.Lock()





# =========================================================

# DATABASE CONNECTION

# =========================================================



def get_db_connection():

    return mysql.connector.connect(

        host=os.getenv("DB_HOST", "localhost"),

        user=os.getenv("DB_USER", "root"),

        password=os.getenv("DB_PASSWORD", ""),

        database=os.getenv(

            "DB_NAME",

            "green_customer_insights"

        ),

    )





def close_db(cursor, connection):

    if cursor:

        cursor.close()



    if connection and connection.is_connected():

        connection.close()





# =========================================================

# COMMON HELPERS

# =========================================================



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





# =========================================================

# HOME AND HEALTH CHECK

# =========================================================



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





# =========================================================

# BRANCHES

# =========================================================



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

            JOIN banks b

                ON b.bank_id = br.bank_id

            WHERE b.is_active = 1

            ORDER BY b.bank_name, br.branch_name

        """)



        return jsonify(cursor.fetchall())



    except mysql.connector.Error:

        app.logger.exception("Branch query failed")



        return error_response(

            "Unable to load branches.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# DEMO OTP

# =========================================================



@app.route("/api/auth/send-demo-otp", methods=["POST"])

def send_demo_otp():

    data = get_data()



    phone = normalize_phone(

        data.get("phone_number")

    )



    if not phone:

        return error_response(

            "Enter a valid phone number."

        )



    otp = f"{secrets.randbelow(1000000):06d}"



    with OTP_LOCK:

        OTP_STORE[phone] = otp



    return jsonify({

        "success": True,

        "message": "Demo OTP generated. No SMS was sent.",

        "demo_otp": otp

    })





# =========================================================

# CUSTOMER REGISTRATION

# =========================================================



@app.route("/api/auth/register", methods=["POST"])

def register():

    data = get_data()



    full_name = str(

        data.get("full_name", "")

    ).strip()



    phone = normalize_phone(

        data.get("phone_number")

    )



    email = str(

        data.get("email", "")

    ).strip().lower()



    password = str(

        data.get("password", "")

    )



    confirm_password = str(

        data.get("confirm_password", "")

    )



    otp = str(

        data.get("otp", "")

    ).strip()



    city = str(

        data.get("city", "")

    ).strip()



    customer_ref = str(

        data.get("customer_ref", "")

    ).strip()



    account_number = str(

        data.get("account_number", "")

    ).strip()



    try:

        branch_id = int(data.get("branch_id"))

    except (TypeError, ValueError):

        return error_response(

            "Select a valid branch."

        )



    if not full_name or len(full_name) > 120:

        return error_response(

            "Enter your full name."

        )



    if not phone:

        return error_response(

            "Enter a valid phone number."

        )



    if len(email) > 150 or not re.fullmatch(

        r"[^@\s]+@[^@\s]+\.[^@\s]+",

        email

    ):

        return error_response(

            "Enter a valid email address."

        )



    if len(password) < 8:

        return error_response(

            "Password must contain at least 8 characters."

        )



    if password != confirm_password:

        return error_response(

            "Passwords do not match."

        )



    if not otp:

        return error_response(

            "Enter the demo OTP."

        )



    if bool(customer_ref) != bool(account_number):

        return error_response(

            "Enter both customer reference and account number "

            "to link an account."

        )



    # Verify demo OTP

    with OTP_LOCK:

        expected_otp = OTP_STORE.get(phone)



        if not expected_otp or not secrets.compare_digest(

            otp,

            expected_otp

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



        # Check selected branch

        cursor.execute("""

            SELECT

                branch_id,

                bank_id,

                city

            FROM branches

            WHERE branch_id = %s

        """, (branch_id,))



        branch = cursor.fetchone()



        if not branch:

            connection.rollback()



            return error_response(

                "Selected branch was not found."

            )



        # Check duplicate user

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



        # Account linking

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

                JOIN customers c

                    ON c.customer_id = a.customer_id

                WHERE a.account_number = %s

                  AND c.customer_ref = %s

                FOR UPDATE

            """, (account_number, customer_ref))



            linked = cursor.fetchone()



            if (

                not linked

                or linked["account_status"] != "Active"

            ):

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



            chosen_branch_id = (

                linked["branch_id"] or branch_id

            )



            cursor.execute("""

                UPDATE customers

                SET

                    phone_number = %s,

                    email = COALESCE(email, %s)

                WHERE customer_id = %s

            """, (

                phone,

                email,

                customer_id

            ))



        # New customer registration

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



            new_customer_ref = (

                "CUST-" + secrets.token_hex(8).upper()

            )



            cursor.execute("""

                INSERT INTO customers (

                    customer_ref,

                    full_name,

                    email,

                    phone_number,

                    city

                )

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



        # Create customer login account

        cursor.execute("""

            INSERT INTO users (

                username,

                password_hash,

                role_id,

                customer_id,

                bank_id,

                branch_id,

                full_name,

                email,

                is_active

            )

            VALUES (

                %s, %s, 1, %s, %s, %s, %s, %s, 1

            )

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

            "A matching record already exists. "

            "Check your phone and email.",

            409

        )



    except mysql.connector.Error:

        if connection:

            connection.rollback()



        app.logger.exception(

            "Registration database error"

        )



        return error_response(

            "Registration failed due to a database error.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# CUSTOMER LOGIN

# =========================================================



@app.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticate a registered customer using email or phone number."""
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

        # The phone number is stored in customers.phone_number and may also
        # be used as users.username for accounts created through registration.
        cursor.execute(
            """
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
                r.role_name,
                c.phone_number
            FROM users AS u
            JOIN roles AS r
                ON r.role_id = u.role_id
            LEFT JOIN customers AS c
                ON c.customer_id = u.customer_id
            WHERE u.username = %s
               OR u.email = %s
               OR c.phone_number = %s
            LIMIT 1
            """,
            (identifier, identifier, identifier),
        )

        user = cursor.fetchone()

        if not user or not user.get("is_active"):
            return error_response(
                "Invalid phone number/email or password.",
                401,
            )

        # Existing registration stores Werkzeug password hashes.
        try:
            password_is_valid = check_password_hash(
                user["password_hash"], password
            )
        except (TypeError, ValueError):
            password_is_valid = False

        if not password_is_valid:
            return error_response(
                "Invalid phone number/email or password.",
                401,
            )

        # Keep the project's existing convention: role_id 1 is Customer.
        if user["role_id"] != 1 or not user.get("customer_id"):
            return error_response(
                "Please use the sign-in page for your account type.",
                403,
            )

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "user": {
                "user_id": user["user_id"],
                "customer_id": user["customer_id"],
                "full_name": user["full_name"],
                "phone_number": user.get("phone_number") or user["username"],
                "email": user["email"],
                "role": user["role_name"],
                "bank_id": user["bank_id"],
                "branch_id": user["branch_id"],
            },
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Customer login database error")
        return error_response(
            "Login failed due to a database error.",
            500,
        )

    finally:
        close_db(cursor, connection)



# =========================================================

# CUSTOMER 360 DASHBOARD

# =========================================================



@app.route(

    "/api/customer/dashboard/<int:user_id>",

    methods=["GET"]

)

def customer_dashboard(user_id):

    connection = None

    cursor = None



    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)



        cursor.execute("""

            SELECT

                u.user_id,

                u.customer_id,

                u.full_name AS account_name,

                u.email AS account_email,

                u.username,

                c.customer_ref,

                c.full_name,

                c.email,

                c.phone_number,

                c.city,

                c.digital_banking,

                c.home_owner,

                c.paper_statement,

                c.solar_interest,

                c.vehicle_type,

                c.created_at

            FROM users u

            JOIN customers c

                ON u.customer_id = c.customer_id

            WHERE u.user_id = %s

              AND u.role_id = 1

              AND u.is_active = 1

            LIMIT 1

        """, (user_id,))



        customer = cursor.fetchone()



        if not customer:

            return error_response(

                "Customer account not found or inactive.",

                404

            )



        return jsonify({

            "success": True,

            "message": "Customer dashboard loaded successfully.",

            "customer": customer

        })



    except mysql.connector.Error:

        app.logger.exception(

            "Customer dashboard query failed"

        )



        return error_response(

            "Unable to load customer dashboard.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# CUSTOMER RECOMMENDATIONS

# =========================================================



@app.route(

    "/api/customer/recommendations/<int:user_id>",

    methods=["GET"]

)

def customer_recommendations(user_id):

    connection = None

    cursor = None



    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)



        # Verify active customer

        cursor.execute("""

            SELECT customer_id

            FROM users

            WHERE user_id = %s

              AND role_id = 1

              AND is_active = 1

            LIMIT 1

        """, (user_id,))



        user = cursor.fetchone()



        if not user or not user["customer_id"]:

            return error_response(

                "Customer account not found.",

                404

            )



        customer_id = user["customer_id"]



        # Fetch only this customer's recommendations

        cursor.execute("""

            SELECT

                r.recommendation_id,

                r.customer_id,

                r.product_id,

                gp.product_name,

                CAST(r.propensity_score AS DOUBLE)

                    AS propensity_score,

                r.model_version,

                r.reason_codes,

                r.evidence_snapshot,

                r.ai_explanation,

                r.recommendation_status,

                r.recommended_at,

                r.updated_at

            FROM recommendations r

            JOIN green_products gp

                ON gp.product_id = r.product_id

            WHERE r.customer_id = %s

            ORDER BY r.recommended_at DESC

        """, (customer_id,))



        recommendations = cursor.fetchall()



        return jsonify({

            "success": True,

            "customer_id": customer_id,

            "total_recommendations": len(recommendations),

            "recommendations": recommendations

        })



    except mysql.connector.Error:

        app.logger.exception(

            "Customer recommendations query failed"

        )



        return error_response(

            "Unable to load customer recommendations.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# EMPLOYEE LOGIN

# =========================================================



@app.route(

    "/api/employee/login",

    methods=["POST"]

)

def employee_login():

    data = get_data()



    identifier = str(

        data.get("username")

        or data.get("email")

        or ""

    ).strip()



    password = str(

        data.get("password", "")

    )



    if not identifier or not password:

        return error_response(

            "Enter your employee username and password."

        )



    connection = None

    cursor = None



    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)



        # Verify employee role, active status and bank assignment

        cursor.execute("""

            SELECT

                u.user_id,

                u.username,

                u.full_name,

                u.email,

                u.password_hash,

                u.role_id,

                u.branch_id,

                u.is_active,

                r.role_name,

                ob.bank_id,

                b.bank_name,

                br.branch_name,

                br.city

            FROM users u

            JOIN roles r

                ON r.role_id = u.role_id

            JOIN officer_banks ob

                ON ob.officer_user_id = u.user_id

            JOIN banks b

                ON b.bank_id = ob.bank_id

            LEFT JOIN branches br

                ON br.branch_id = u.branch_id

               AND br.bank_id = ob.bank_id

            WHERE (u.username = %s OR u.email = %s)

              AND u.role_id = 3

              AND u.is_active = 1

              AND b.is_active = 1

            LIMIT 1

        """, (

            identifier,

            identifier

        ))



        employee = cursor.fetchone()



        if not employee:

            return error_response(

                "Invalid employee credentials or bank assignment.",

                401

            )



        if not check_password_hash(

            employee["password_hash"],

            password

        ):

            return error_response(

                "Invalid employee credentials.",

                401

            )



        return jsonify({

            "success": True,

            "message": "Employee login successful.",

            "employee": {

                "user_id": employee["user_id"],

                "username": employee["username"],

                "full_name": employee["full_name"],

                "email": employee["email"],

                "role_id": employee["role_id"],

                "role_name": employee["role_name"],

                "bank_id": employee["bank_id"],

                "bank_name": employee["bank_name"],

                "branch_id": employee["branch_id"],

                "branch_name": employee["branch_name"],

                "city": employee["city"]

            }

        })



    except mysql.connector.Error:

        app.logger.exception(

            "Employee login database error"

        )



        return error_response(

            "Employee login failed due to a database error.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# EMPLOYEE DASHBOARD

# =========================================================



@app.route(

    "/api/employee/dashboard/<int:user_id>",

    methods=["GET"]

)

def employee_dashboard(user_id):

    connection = None

    cursor = None



    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)



        # Verify employee and assigned bank

        cursor.execute("""

            SELECT

                u.user_id,

                u.full_name,

                u.email,

                u.branch_id,

                ob.bank_id,

                b.bank_name,

                br.branch_name,

                br.city

            FROM users u

            JOIN officer_banks ob

                ON ob.officer_user_id = u.user_id

            JOIN banks b

                ON b.bank_id = ob.bank_id

            LEFT JOIN branches br

                ON br.branch_id = u.branch_id

               AND br.bank_id = ob.bank_id

            WHERE u.user_id = %s

              AND u.role_id = 3

              AND u.is_active = 1

              AND b.is_active = 1

            LIMIT 1

        """, (user_id,))



        employee = cursor.fetchone()



        if not employee:

            return error_response(

                "Employee not found or not authorized.",

                404

            )



        bank_id = employee["bank_id"]



        # Count customers belonging to this bank

        cursor.execute("""

            SELECT COUNT(DISTINCT a.customer_id)

                AS total_customers

            FROM accounts a

            WHERE a.bank_id = %s

        """, (bank_id,))



        total_customers = cursor.fetchone()["total_customers"]



        # Count recommendations belonging to this bank

        cursor.execute("""

            SELECT COUNT(*) AS total_recommendations

            FROM recommendations r

            WHERE EXISTS (

                SELECT 1

                FROM accounts a

                WHERE a.customer_id = r.customer_id

                  AND a.bank_id = %s

            )

        """, (bank_id,))



        total_recommendations = cursor.fetchone()[

            "total_recommendations"

        ]



        # Count different green products recommended

        cursor.execute("""

            SELECT COUNT(DISTINCT r.product_id)

                AS total_green_products

            FROM recommendations r

            WHERE EXISTS (

                SELECT 1

                FROM accounts a

                WHERE a.customer_id = r.customer_id

                  AND a.bank_id = %s

            )

        """, (bank_id,))



        total_green_products = cursor.fetchone()[

            "total_green_products"

        ]



        return jsonify({

            "success": True,

            "message": "Employee dashboard loaded successfully.",

            "employee": employee,

            "dashboard": {

                "total_customers": total_customers,

                "total_recommendations": total_recommendations,

                "total_green_products": total_green_products

            }

        })



    except mysql.connector.Error:

        app.logger.exception(

            "Employee dashboard query failed"

        )



        return error_response(

            "Unable to load employee dashboard.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================
# EMPLOYEE BANK-WIDE RECOMMENDATIONS + CUSTOMER DETAILS
# =========================================================



def _as_bool(value):
    """Convert common database boolean values safely; unknown values remain unknown."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "y"):
        return True
    if normalized in ("0", "false", "no", "n"):
        return False
    return None


def build_baseline_prediction(rec):
    """Return a transparent rule-based baseline, not a trained-model prediction."""
    product_name = str(rec.get("product_name") or "").lower()
    if "paperless" not in product_name:
        return {
            "available": False,
            "source": "no_product_specific_rule",
            "prediction": None,
            "propensity_score": None,
            "confidence": None,
            "model_version": None,
            "reason_codes": [],
            "explanation": "A product-specific prediction rule is not configured yet.",
        }

    paper_statement = _as_bool(rec.get("paper_statement"))
    digital_banking = _as_bool(rec.get("digital_banking"))
    score = 50
    reasons = []

    if paper_statement is True:
        score += 25
        reasons.append("CURRENT_PAPER_STATEMENTS")
    elif paper_statement is False:
        score -= 20
        reasons.append("NO_CURRENT_PAPER_STATEMENTS")

    if digital_banking is True:
        score += 15
        reasons.append("DIGITAL_BANKING_ENABLED")
    elif digital_banking is False:
        score -= 10
        reasons.append("DIGITAL_BANKING_NOT_ENABLED")

    score = max(0, min(100, score))
    if score >= 70:
        label = "High propensity"
    elif score >= 45:
        label = "Moderate propensity"
    else:
        label = "Low propensity"

    if not reasons:
        explanation = (
            "Limited customer profile data is available. This is a neutral "
            "rule-based baseline, not a personalized conclusion."
        )
    else:
        explanation = (
            f"{label} for the Go Paperless opportunity based on the available "
            "paper-statement and digital-banking indicators. This is a "
            "rule-based estimate, not a trained-model result."
        )

    return {
        "available": True,
        "source": "explainable_rule_based_baseline",
        "prediction": label,
        "propensity_score": score,
        "score_scale": "0-100",
        "confidence": None,
        "model_version": "rules-v1",
        "reason_codes": reasons,
        "explanation": explanation,
    }

def build_demo_csv_prediction(rec):
    """Return a transparent CSV demo score; this is not a trained ML prediction."""
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "demo_recommendation_scores.csv",
    )

    product_name = str(rec.get("product_name") or "").strip().lower()
    if "paperless" in product_name:
        score_column = "go_paperless_score"
    elif "solar" in product_name:
        score_column = "solar_finance_score"
    elif "ev" in product_name or "electric vehicle" in product_name:
        score_column = "ev_finance_score"
    elif "home loan" in product_name or "green home" in product_name:
        score_column = "green_home_loan_score"
    else:
        return None

    if not os.path.isfile(csv_path):
        return None

    try:
        with open(csv_path, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    row_customer_id = int(row.get("customer_id", ""))
                    raw_score = float(row[score_column])
                except (ValueError, TypeError, KeyError):
                    continue

                if row_customer_id != int(rec["customer_id"]):
                    continue

                # CSV scores are on a 0-1 scale; dashboard scores are 0-100.
                score_100 = round(max(0.0, min(1.0, raw_score)) * 100, 1)
                if score_100 >= 70:
                    label = "High propensity"
                elif score_100 >= 45:
                    label = "Moderate propensity"
                else:
                    label = "Low propensity"

                return {
                    "available": True,
                    "source": "rule_based_demo_score",
                    "prediction": label,
                    "propensity_score": score_100,
                    "score_scale": "0-100",
                    "confidence": None,
                    "model_version": "demo-rules-v1",
                    "reason_codes": ["RULE_BASED_DEMO_SCORE"],
                    "explanation": (
                        "This demonstration score is calculated from customer "
                        "profile and transaction features using transparent rules. "
                        "It is not a trained-model prediction or a calibrated "
                        "purchase probability."
                    ),
                }
    except (OSError, csv.Error):
        app.logger.exception("Unable to read demo recommendation scores CSV")

    return None


@app.route(
    "/api/employee/recommendations/<int:user_id>",
    methods=["GET"]
)
def employee_recommendations(user_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Verify employee and assigned bank.
        cursor.execute("""
            SELECT
                ob.bank_id,
                b.bank_name
            FROM users u
            JOIN officer_banks ob
                ON ob.officer_user_id = u.user_id
            JOIN banks b
                ON b.bank_id = ob.bank_id
            WHERE u.user_id = %s
              AND u.role_id = 3
              AND u.is_active = 1
              AND b.is_active = 1
            LIMIT 1
        """, (user_id,))

        employee = cursor.fetchone()
        if not employee:
            return error_response(
                "Employee not found or not authorized.", 404
            )

        bank_id = employee["bank_id"]

        # Load actual customer data and the recommendations saved in MySQL.
        # Account numbers are returned by the API for the authorized employee;
        # the frontend should mask them in the customer table.
        cursor.execute("""
            SELECT
                r.recommendation_id,
                r.customer_id,
                c.customer_ref,
                c.full_name AS customer_name,
                c.email,
                c.phone_number,
                c.city,
                c.digital_banking,
                c.paper_statement,
                (
                    SELECT a.account_number
                    FROM accounts a
                    WHERE a.customer_id = c.customer_id
                      AND a.bank_id = %s
                    ORDER BY a.account_id
                    LIMIT 1
                ) AS account_number,
                r.product_id,
                gp.product_name,
                CAST(r.propensity_score AS DOUBLE) AS propensity_score,
                r.model_version,
                r.reason_codes,
                r.evidence_snapshot,
                r.ai_explanation,
                r.recommendation_status,
                r.recommended_at,
                r.updated_at
            FROM recommendations r
            JOIN green_products gp
                ON gp.product_id = r.product_id
            JOIN customers c
                ON c.customer_id = r.customer_id
            WHERE EXISTS (
                SELECT 1
                FROM accounts a
                WHERE a.customer_id = r.customer_id
                  AND a.bank_id = %s
            )
            ORDER BY r.recommended_at DESC
        """, (bank_id, bank_id))

        recommendations = cursor.fetchall()
        customers_by_id = {}

        for rec in recommendations:
            customer_id = rec["customer_id"]

            if customer_id not in customers_by_id:
                customers_by_id[customer_id] = {
                    "customer_id": customer_id,
                    "customer_name": rec.get("customer_name"),
                    "customer_ref": rec.get("customer_ref"),
                    "account_number": rec.get("account_number"),
                    "email": rec.get("email"),
                    "phone": rec.get("phone_number"),
                    "city": rec.get("city"),
                    # The provided schema/query does not establish a segment field.
                    "customer_segment": None,
                    "recommendations": []
                }

            propensity = rec.get("propensity_score")
            model_version = rec.get("model_version")

            if propensity is not None and model_version:
                stored_score = float(propensity)
                score_100 = stored_score * 100 if 0 <= stored_score <= 1 else stored_score
                score_100 = max(0.0, min(100.0, score_100))
                if score_100 >= 70:
                    prediction_label = "High propensity"
                elif score_100 >= 45:
                    prediction_label = "Moderate propensity"
                else:
                    prediction_label = "Low propensity"

                rec["ai_prediction"] = {
                    "available": True,
                    "source": "stored_model_result",
                    "prediction": prediction_label,
                    "propensity_score": round(score_100, 1),
                    "score_scale": "0-100",
                    "confidence": None,
                    "model_version": model_version,
                    "reason_codes": rec.get("reason_codes"),
                    "explanation": rec.get("ai_explanation"),
                    "evidence": rec.get("evidence_snapshot"),
                }
            else:
                demo_prediction = build_demo_csv_prediction(rec)
                rec["ai_prediction"] = (
                    demo_prediction
                    if demo_prediction is not None
                    else build_baseline_prediction(rec)
                )

            customers_by_id[customer_id]["recommendations"].append(rec)

        customers = list(customers_by_id.values())

        return jsonify({
            "success": True,
            "bank_id": bank_id,
            "bank_name": employee["bank_name"],
            "total_recommendations": len(recommendations),
            "total_customers": len(customers),
            "customers": customers,
            "recommendations": recommendations
        })

    except mysql.connector.Error:
        app.logger.exception("Employee recommendations query failed")
        return error_response(
            "Unable to load employee recommendations.", 500
        )

    finally:
        close_db(cursor, connection)



# =========================================================

# DASHBOARD SUMMARY

# =========================================================



@app.route("/api/dashboard/summary")

def dashboard_summary():

    connection = None

    cursor = None



    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)



        cursor.execute("""

            SELECT

                (SELECT COUNT(*) FROM banks)

                    AS total_banks,



                (SELECT COUNT(*) FROM customers)

                    AS total_customers,



                (SELECT COUNT(*) FROM accounts)

                    AS total_accounts,



                (SELECT COUNT(*) FROM transactions)

                    AS total_transactions

        """)



        return jsonify(cursor.fetchone())



    except mysql.connector.Error:

        app.logger.exception(

            "Dashboard summary failed"

        )



        return error_response(

            "Unable to load dashboard summary.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# BANKS

# =========================================================



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

                COUNT(DISTINCT c.customer_id)

                    AS customer_count,

                COUNT(DISTINCT t.transaction_id)

                    AS transaction_count

            FROM banks b

            LEFT JOIN accounts a

                ON a.bank_id = b.bank_id

            LEFT JOIN customers c

                ON c.customer_id = a.customer_id

            LEFT JOIN transactions t

                ON t.account_id = a.account_id

            GROUP BY

                b.bank_id,

                b.bank_name

            ORDER BY b.bank_id

        """)



        return jsonify(cursor.fetchall())



    except mysql.connector.Error:

        app.logger.exception(

            "Banks query failed"

        )



        return error_response(

            "Unable to load banks.",

            500

        )



    finally:

        close_db(cursor, connection)





# =========================================================

# START SERVER

# =========================================================



if __name__ == "__main__":

    app.run(

        debug=True,

        port=5000

    )
