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
    """Fetch analytics data from the restaurant_dw database."""

    connection = get_dw_connection()

    try:
        with connection.cursor() as cursor:

            # 1. KPI CARDS: Revenue, Transactions, Average Order Value
            cursor.execute("""
                SELECT
                    COALESCE(SUM(subtotal), 0) AS total_revenue,
                    COUNT(DISTINCT order_id) AS total_orders,
                    CASE
                        WHEN COUNT(DISTINCT order_id) > 0
                        THEN SUM(subtotal) / COUNT(DISTINCT order_id)
                        ELSE 0
                    END AS average_order_value
                FROM fact_sales
            """)

            kpis = cursor.fetchone()

            # 2. BAR CHART: Top 5 Best-Selling Menu Items
            cursor.execute("""
                SELECT
                    m.item_name,
                    SUM(f.quantity) AS total_quantity_sold,
                    SUM(f.subtotal) AS item_revenue
                FROM fact_sales f
                JOIN dim_menu_item m
                    ON f.item_key = m.item_key
                GROUP BY m.item_key, m.item_name
                ORDER BY total_quantity_sold DESC
                LIMIT 5
            """)

            top_items = cursor.fetchall()

            # 3. LINE CHART: Daily Revenue Trend
            # Latest 7 recorded dates, displayed chronologically in JS.
            cursor.execute("""
                SELECT
                    t.date_val,
                    SUM(f.subtotal) AS daily_revenue
                FROM fact_sales f
                JOIN dim_time t
                    ON f.time_key = t.time_key
                GROUP BY t.date_val
                ORDER BY t.date_val DESC
                LIMIT 7
            """)

            recent_sales = cursor.fetchall()

            # 4. DONUT CHART: Revenue Distribution by Menu Category
            cursor.execute("""
                SELECT
                    COALESCE(
                        NULLIF(m.category_name, ''),
                        'Uncategorized'
                    ) AS category_name,
                    SUM(f.subtotal) AS category_revenue,
                    SUM(f.quantity) AS category_quantity
                FROM fact_sales f
                JOIN dim_menu_item m
                    ON f.item_key = m.item_key
                GROUP BY
                    COALESCE(
                        NULLIF(m.category_name, ''),
                        'Uncategorized'
                    )
                ORDER BY category_revenue DESC
            """)

            category_breakdown = cursor.fetchall()

        return {
            "kpis": kpis,
            "top_items": top_items,
            "recent_sales": recent_sales,
            "category_breakdown": category_breakdown
        }

    finally:
        connection.close()



####################### New Entries ##################################E

# ---------- EMPLOYEE CRUD ----------

@app.route("/staff/new", methods=["GET", "POST"])
@owner_required
def staff_create():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not all([first_name, last_name, username, password]):
            flash("All fields are required.", "error")
            return render_template("staff_form.html", employee=None)

        if role not in ("Cashier", "Waiter", "Chef", "Manager", "Owner"):
            flash("Invalid role.", "error")
            return render_template("staff_form.html", employee=None)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO staff
                        (first_name, last_name, username,
                         password_hash, role, hire_date, is_active)
                    VALUES (%s, %s, %s, %s, %s, CURDATE(), 1)
                """, (
                    first_name, last_name, username,
                    generate_password_hash(password), role
                ))
            conn.commit()
            flash("Employee created successfully.", "success")
            return redirect(url_for("staff_list"))

        except pymysql.MySQLError as exc:
            conn.rollback()
            if exc.args and exc.args[0] == 1062:
                flash("That username is already in use.", "error")
            else:
                app.logger.exception("Unable to create employee")
                flash("Could not create employee.", "error")
        finally:
            conn.close()

    return render_template("staff_form.html", employee=None)


@app.route("/staff/<int:staff_id>/edit", methods=["GET", "POST"])
@owner_required
def staff_edit(staff_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT staff_id, first_name, last_name,
                       username, role, hire_date, is_active
                FROM staff WHERE staff_id = %s
            """, (staff_id,))
            employee = cur.fetchone()

        if not employee:
            abort(404)

        if request.method == "POST":
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            username = request.form.get("username", "").strip()
            role = request.form.get("role", "")
            password = request.form.get("password", "")
            is_active = 1 if request.form.get("is_active") == "1" else 0

            if not all([first_name, last_name, username]):
                flash("Name and username are required.", "error")
                return render_template(
                    "staff_form.html", employee=employee
                )

            if role not in ("Owner", "Manager", "Staff"):
                flash("Invalid role.", "error")
                return render_template(
                    "staff_form.html", employee=employee
                )

            # Prevent an owner from accidentally disabling their own
            # currently logged-in account.
            if (
                staff_id == session["staff_id"]
                and (is_active == 0 or role != "Owner")
            ):
                flash(
                    "You cannot disable or demote your own account here.",
                    "error"
                )
                return render_template(
                    "staff_form.html", employee=employee
                )

            with conn.cursor() as cur:
                if password:
                    cur.execute("""
                        UPDATE staff
                        SET first_name=%s, last_name=%s, username=%s,
                            role=%s, is_active=%s, password_hash=%s
                        WHERE staff_id=%s
                    """, (
                        first_name, last_name, username, role,
                        is_active, generate_password_hash(password),
                        staff_id
                    ))
                else:
                    cur.execute("""
                        UPDATE staff
                        SET first_name=%s, last_name=%s, username=%s,
                            role=%s, is_active=%s
                        WHERE staff_id=%s
                    """, (
                        first_name, last_name, username, role,
                        is_active, staff_id
                    ))

            conn.commit()
            flash("Employee updated successfully.", "success")
            return redirect(url_for("staff_list"))

        return render_template("staff_form.html", employee=employee)

    except pymysql.MySQLError as exc:
        conn.rollback()
        if exc.args and exc.args[0] == 1062:
            flash("That username is already in use.", "error")
        else:
            app.logger.exception("Unable to update employee")
            flash("Could not update employee.", "error")
        return redirect(url_for("staff_list"))
    finally:
        conn.close()


@app.post("/staff/<int:staff_id>/delete")
@owner_required
def staff_delete(staff_id):
    if staff_id == session["staff_id"]:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("staff_list"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM staff WHERE staff_id = %s",
                (staff_id,)
            )
            deleted = cur.rowcount

        conn.commit()
        flash(
            "Employee deleted." if deleted else "Employee not found.",
            "success" if deleted else "error"
        )

    except pymysql.MySQLError:
        conn.rollback()
        app.logger.exception("Unable to delete employee")
        flash(
            "Employee could not be deleted. They may have linked orders. "
            "Deactivate the account instead.",
            "error"
        )
    finally:
        conn.close()

    return redirect(url_for("staff_list"))


# ---------- ORDER CRUD ----------

ORDER_STATUSES = (
    "Pending", "Preparing", "Ready", "Completed", "Cancelled"
)


@app.route("/orders")
@login_required
def order_list():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, o.customer_id, o.staff_id,
                       o.order_status, o.total_amount, o.created_at,
                       COUNT(od.order_detail_id) AS item_count,
                       COALESCE(SUM(od.quantity), 0) AS total_quantity
                FROM orders o
                LEFT JOIN order_details od ON od.order_id = o.order_id
                GROUP BY o.order_id, o.customer_id, o.staff_id,
                         o.order_status, o.total_amount, o.created_at
                ORDER BY o.created_at DESC
            """)
            orders = cur.fetchall()

        return render_template(
            "orders.html",
            orders=orders,
            statuses=ORDER_STATUSES
        )
    finally:
        conn.close()




from decimal import Decimal, InvalidOperation


@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def order_create():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, first_name, last_name, email
                FROM customers
                ORDER BY first_name, last_name
            """)
            customers = cur.fetchall()

            cur.execute("""
                SELECT staff_id, first_name, last_name
                FROM staff
                WHERE is_active = 1
                ORDER BY first_name, last_name
            """)
            employees = cur.fetchall()

            cur.execute("""
                SELECT item_id, item_name, category, price, stock_level
                FROM menu_items
                WHERE is_available = 1
                ORDER BY category, item_name
            """)
            menu_items = cur.fetchall()

        if request.method == "GET":
            return render_template(
                "order_form.html",
                order=None,
                customers=customers,
                employees=employees,
                menu_items=menu_items,
                statuses=ORDER_STATUSES
            )

        # Validate customer selection.
        customer_mode = request.form.get("customer_mode", "existing")
        customer_id = None

        # Validate the staff member.
        staff_value = request.form.get("staff_id", "").strip()
        try:
            staff_id = int(staff_value) if staff_value else session["staff_id"]
        except (ValueError, TypeError):
            flash("Invalid staff selection.", "error")
            return redirect(url_for("order_create"))

        # Read item IDs and quantities from repeated form fields.
        item_ids = request.form.getlist("item_id[]")
        quantities = request.form.getlist("quantity[]")

        if not item_ids or len(item_ids) != len(quantities):
            flash("Add at least one menu item.", "error")
            return redirect(url_for("order_create"))

        # Combine duplicate menu-item selections.
        requested_items = {}
        try:
            for raw_id, raw_qty in zip(item_ids, quantities):
                item_id = int(raw_id)
                quantity = int(raw_qty)

                if item_id <= 0 or quantity <= 0:
                    raise ValueError

                requested_items[item_id] = (
                    requested_items.get(item_id, 0) + quantity
                )

        except (ValueError, TypeError):
            flash("Choose valid menu items and quantities.", "error")
            return redirect(url_for("order_create"))

        if any(qty > 1000 for qty in requested_items.values()):
            flash("The requested quantity is too large.", "error")
            return redirect(url_for("order_create"))

        payment_method = request.form.get("payment_method", "").strip()
        payment_status = request.form.get("payment_status", "Pending")

        valid_methods = ("Cash", "Credit Card", "Mobile Wallet")
        valid_payment_statuses = ("Pending", "Paid", "Failed", "Refunded")

        if payment_method and payment_method not in valid_methods:
            flash("Invalid payment method.", "error")
            return redirect(url_for("order_create"))

        if payment_status not in valid_payment_statuses:
            flash("Invalid payment status.", "error")
            return redirect(url_for("order_create"))

        conn.begin()

        with conn.cursor() as cur:
            # Create a customer if requested.
            if customer_mode == "new":
                first_name = request.form.get("new_first_name", "").strip()
                last_name = request.form.get("new_last_name", "").strip()
                email = request.form.get("new_email", "").strip()
                phone = request.form.get("new_phone_number", "").strip()

                if not first_name or not last_name or not email:
                    raise ValueError(
                        "New customers require a first name, last name, and email."
                    )

                if (
                    len(first_name) > 50
                    or len(last_name) > 50
                    or len(email) > 100
                    or len(phone) > 20
                    or "@" not in email
                ):
                    raise ValueError("Invalid customer details.")

                cur.execute("""
                    INSERT INTO customers
                        (first_name, last_name, email, phone_number)
                    VALUES (%s, %s, %s, %s)
                """, (first_name, last_name, email, phone or None))

                customer_id = cur.lastrowid

            elif customer_mode == "existing":
                raw_customer = request.form.get("customer_id", "").strip()

                if not raw_customer:
                    raise ValueError("Select a customer or choose walk-in.")

                try:
                    customer_id = int(raw_customer)
                except ValueError:
                    raise ValueError("Invalid customer selection.")

                cur.execute("""
                    SELECT customer_id FROM customers
                    WHERE customer_id = %s
                """, (customer_id,))

                if not cur.fetchone():
                    raise ValueError("The selected customer does not exist.")

            elif customer_mode != "walkin":
                raise ValueError("Invalid customer option.")

            # Confirm the staff account is active.
            cur.execute("""
                SELECT staff_id FROM staff
                WHERE staff_id = %s AND is_active = 1
            """, (staff_id,))

            if not cur.fetchone():
                raise ValueError("The selected staff member is not active.")

            # Lock menu rows so concurrent orders cannot oversell stock.
            total = Decimal("0.00")
            order_lines = []

            for item_id, quantity in sorted(requested_items.items()):
                cur.execute("""
                    SELECT item_id, item_name, price, stock_level
                    FROM menu_items
                    WHERE item_id = %s AND is_available = 1
                    FOR UPDATE
                """, (item_id,))

                item = cur.fetchone()

                if not item:
                    raise ValueError(
                        f"Menu item #{item_id} is unavailable."
                    )

                if item["stock_level"] is not None:
                    if item["stock_level"] < quantity:
                        raise ValueError(
                            f"Not enough stock for {item['item_name']}."
                        )

                subtotal = (
                    Decimal(str(item["price"])) * quantity
                ).quantize(Decimal("0.01"))

                total += subtotal
                order_lines.append({
                    "item_id": item_id,
                    "quantity": quantity,
                    "subtotal": subtotal,
                    "stock_level": item["stock_level"],
                    "item_name": item["item_name"]
                })

            total = total.quantize(Decimal("0.01"))

            if total > Decimal("99999999.99"):
                raise ValueError("Order total exceeds the database limit.")

            # Create the order using the calculated total.
            cur.execute("""
                INSERT INTO orders
                    (customer_id, staff_id, order_status, total_amount)
                VALUES (%s, %s, 'Pending', %s)
            """, (customer_id, staff_id, total))

            order_id = cur.lastrowid

            # Add order details and reduce stock.
            for line in order_lines:
                cur.execute("""
                    INSERT INTO order_details
                        (order_id, item_id, quantity, subtotal)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    line["item_id"],
                    line["quantity"],
                    line["subtotal"]
                ))

                if line["stock_level"] is not None:
                    cur.execute("""
                        UPDATE menu_items
                        SET stock_level = stock_level - %s
                        WHERE item_id = %s
                    """, (line["quantity"], line["item_id"]))

            # A payment record is optional.
            if payment_method:
                cur.execute("""
                    INSERT INTO payments
                        (order_id, amount_paid, payment_method, payment_status)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    total if payment_status == "Paid" else Decimal("0.00"),
                    payment_method,
                    payment_status
                ))

        conn.commit()
        flash(
            f"Order #{order_id} created. Total: {total:.2f}",
            "success"
        )
        return redirect(url_for("order_list"))

    except ValueError as exc:
        conn.rollback()
        flash(str(exc), "error")
        return redirect(url_for("order_create"))

    except pymysql.MySQLError as exc:
        conn.rollback()

        if exc.args and exc.args[0] == 1062:
            flash("That customer email is already registered.", "error")
        else:
            app.logger.exception("Order creation failed")
            flash("Order creation failed; no changes were saved.", "error")

        return redirect(url_for("order_create"))

    finally:
        conn.close()



@app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def order_edit(order_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE order_id = %s",
                (order_id,)
            )
            order = cur.fetchone()

            if not order:
                abort(404)

            cur.execute("""
                SELECT customer_id FROM customers ORDER BY customer_id
            """)
            customers = cur.fetchall()

            cur.execute("""
                SELECT staff_id, first_name, last_name
                FROM staff WHERE is_active = 1 OR staff_id = %s
                ORDER BY first_name, last_name
            """, (order["staff_id"],))
            employees = cur.fetchall()

        if request.method == "POST":
            customer_value = request.form.get("customer_id", "").strip()
            staff_value = request.form.get("staff_id", "").strip()
            status = request.form.get("order_status", "")
            amount_value = request.form.get("total_amount", "").strip()

            if status not in ORDER_STATUSES:
                flash("Invalid order status.", "error")
                return redirect(url_for("order_edit", order_id=order_id))

            try:
                customer_id = int(customer_value) if customer_value else None
                staff_id = int(staff_value) if staff_value else None
                total_amount = float(amount_value)
                if total_amount < 0:
                    raise ValueError
            except (ValueError, TypeError):
                flash("Enter valid order values.", "error")
                return redirect(url_for("order_edit", order_id=order_id))

            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders
                    SET customer_id=%s, staff_id=%s,
                        order_status=%s, total_amount=%s
                    WHERE order_id=%s
                """, (
                    customer_id, staff_id, status,
                    total_amount, order_id
                ))

            conn.commit()
            flash("Order updated.", "success")
            return redirect(url_for("order_list"))

        return render_template(
            "order_form.html", order=order,
            customers=customers, employees=employees,
            statuses=ORDER_STATUSES
        )
    except pymysql.MySQLError:
        conn.rollback()
        app.logger.exception("Unable to update order")
        flash("Could not update order. Check its linked records.", "error")
        return redirect(url_for("order_list"))
    finally:
        conn.close()


@app.post("/orders/<int:order_id>/delete")
@login_required
def order_delete(order_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Delete child rows first to satisfy foreign-key constraints.
            cur.execute(
                "DELETE FROM order_details WHERE order_id = %s",
                (order_id,)
            )
            cur.execute(
                "DELETE FROM orders WHERE order_id = %s",
                (order_id,)
            )
            deleted = cur.rowcount

        conn.commit()
        flash(
            "Order deleted." if deleted else "Order not found.",
            "success" if deleted else "error"
        )
    except pymysql.MySQLError:
        conn.rollback()
        app.logger.exception("Unable to delete order")
        flash(
            "Order could not be deleted. Check linked payments or records.",
            "error"
        )
    finally:
        conn.close()

    return redirect(url_for("order_list"))



@app.route("/dashboard/operational")
@login_required
def operational_dashboard():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            # Order counts by status
            cur.execute("""
                SELECT
                    COUNT(*) AS total_orders,
                    COALESCE(SUM(order_status = 'Pending'), 0) AS pending_orders,
                    COALESCE(SUM(order_status = 'Preparing'), 0) AS preparing_orders,
                    COALESCE(SUM(order_status = 'Ready'), 0) AS ready_orders,
                    COALESCE(SUM(order_status = 'Completed'), 0) AS completed_orders,
                    COALESCE(SUM(order_status = 'Cancelled'), 0) AS cancelled_orders
                FROM orders
            """)
            order_stats = cur.fetchone()

            # Revenue from completed orders
            cur.execute("""
                SELECT
                    COALESCE(SUM(o.total_amount), 0) AS total_revenue,
                    COUNT(*) AS completed_orders
                FROM orders o
                WHERE o.order_status = 'Completed'
            """)
            revenue_stats = cur.fetchone()

            # Payments overview
            cur.execute("""
                SELECT
                    COALESCE(SUM(
                        CASE WHEN payment_status = 'Paid'
                             THEN amount_paid ELSE 0 END
                    ), 0) AS total_paid,
                    COUNT(*) AS payment_count,
                    SUM(payment_status = 'Pending') AS pending_payments,
                    SUM(payment_status = 'Failed') AS failed_payments
                FROM payments
            """)
            payment_stats = cur.fetchone()

            # Recent orders with customer and staff details
            cur.execute("""
                SELECT
                    o.order_id,
                    o.order_status,
                    o.total_amount,
                    o.created_at,
                    COALESCE(
                        CONCAT(c.first_name, ' ', c.last_name),
                        'Walk-in Customer'
                    ) AS customer_name,
                    COALESCE(
                        CONCAT(s.first_name, ' ', s.last_name),
                        'Unassigned'
                    ) AS staff_name
                FROM orders o
                LEFT JOIN customers c
                    ON c.customer_id = o.customer_id
                LEFT JOIN staff s
                    ON s.staff_id = o.staff_id
                ORDER BY o.created_at DESC
                LIMIT 10
            """)
            recent_orders = cur.fetchall()

            # Current menu availability
            cur.execute("""
                SELECT
                    COUNT(*) AS total_items,
                    COALESCE(SUM(is_available = 1), 0) AS available_items,
                    COALESCE(SUM(stock_level <= 5), 0) AS low_stock_items
                FROM menu_items
            """)
            menu_stats = cur.fetchone()

            # Daily revenue for the last 7 days, including days with no sales
            cur.execute("""
                SELECT
                    DATE(o.created_at) AS sale_date,
                    COALESCE(SUM(o.total_amount), 0) AS daily_revenue
                FROM orders o
                WHERE o.order_status = 'Completed'
                  AND o.created_at >= CURDATE() - INTERVAL 6 DAY
                  AND o.created_at < CURDATE() + INTERVAL 1 DAY
                GROUP BY DATE(o.created_at)
                ORDER BY sale_date
            """)
            daily_revenue = cur.fetchall()

            # Sales distribution by order status
            cur.execute("""
                SELECT order_status, COUNT(*) AS order_count
                FROM orders
                GROUP BY order_status
                ORDER BY FIELD(
                    order_status,
                    'Pending', 'Preparing', 'Ready', 'Completed', 'Cancelled'
                )
            """)
            status_breakdown = cur.fetchall()

            # Top 5 menu items by quantity sold
            cur.execute("""
                SELECT
                    m.item_name,
                    SUM(od.quantity) AS quantity_sold,
                    SUM(od.subtotal) AS revenue
                FROM order_details od
                JOIN orders o ON o.order_id = od.order_id
                JOIN menu_items m ON m.item_id = od.item_id
                WHERE o.order_status = 'Completed'
                GROUP BY m.item_id, m.item_name
                ORDER BY quantity_sold DESC
                LIMIT 5
            """)
            top_items = cur.fetchall()

        return render_template(
            "operational_dashboard.html",
            order_stats=order_stats,
            revenue_stats=revenue_stats,
            payment_stats=payment_stats,
            recent_orders=recent_orders,
            top_items=top_items,
            menu_stats=menu_stats,
            daily_revenue=daily_revenue,
            status_breakdown=status_breakdown
        )
    finally:
        conn.close()




if __name__ == '__main__':
    app.run(debug=True, port=6767)
