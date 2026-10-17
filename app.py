from flask import Flask, render_template, jsonify
import pymysql
import os
from functools import wraps
from dotenv import load_dotenv

load_dotenv()
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
import pymysql
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]

DB_CONFIG = {
    "host": "localhost",
    "user": os.environ.get("DB_USER", "ali"),
    "password": os.environ["DB_PASSWORD"],
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": False,
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG, database="restaurant")

def get_dw_connection():
    return pymysql.connect(**DB_CONFIG, database="restaurant_dw")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "staff_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def owner_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "Owner":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()  # restaurant, not restaurant_dw

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT staff_id, first_name, last_name,
                           role, password_hash
                    FROM staff
                    WHERE username = %s AND is_active = 1
                    LIMIT 1
                """, (username,))
                staff = cur.fetchone()
        finally:
            conn.close()

        if staff and staff["password_hash"] and check_password_hash(
            staff["password_hash"], password
        ):
            session.clear()
            session["staff_id"] = staff["staff_id"]
            session["name"] = (
                f'{staff["first_name"]} {staff["last_name"]}'
            )
            session["role"] = staff["role"]
            return redirect(url_for("index"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")

@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    data = fetch_dashboard_data()
    return render_template("dashboard.html", data=data)

@app.route("/staff")
@owner_required
def staff_list():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT staff_id, first_name, last_name, role,
                       hire_date, username, is_active
                FROM staff
                ORDER BY staff_id
            """)
            employees = cur.fetchall()
    finally:
        conn.close()

    return render_template("staff.html", employees=employees)

@app.errorhandler(403)
def forbidden(error):
    return "403 — You do not have permission to access this page.", 403

def fetch_dashboard_data():
    """Queries restaurant_dw using your exact table and column structures."""
    connection = get_dw_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Total Revenue & Total Orders (using 'subtotal' from fact_sales)
            cursor.execute("""
                SELECT
                    COALESCE(SUM(subtotal), 0) AS total_revenue,
                    COUNT(DISTINCT order_id) AS total_orders
                FROM fact_sales;
            """)
            kpis = cursor.fetchone()
            
            print("DEBUG KPI:", repr(kpis))
            # 2. Top 5 Best-Selling Menu Items (using 'subtotal' and 'item_name')
            cursor.execute("""
                SELECT 
                    m.item_name,
                    SUM(f.quantity) AS total_quantity_sold,
                    SUM(f.subtotal) AS item_revenue
                FROM fact_sales f
                JOIN dim_menu_item m ON f.item_key = m.item_key
                GROUP BY m.item_name
                ORDER BY item_revenue DESC
                LIMIT 5;
            """)
            top_items = cursor.fetchall()

            # 3. Sales Trend by Date (using 'date_val' from dim_time)
            cursor.execute("""
                SELECT 
                    t.date_val,
                    SUM(f.subtotal) AS daily_revenue
                FROM fact_sales f
                JOIN dim_time t ON f.time_key = t.time_key
                GROUP BY t.date_val
                ORDER BY t.date_val DESC
                LIMIT 7;
            """)
            recent_sales = cursor.fetchall()

        return {
            "kpis": kpis,
            "top_items": top_items,
            "recent_sales": recent_sales
        }
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=True, port=6767)
