from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
import sqlite3
import os
import re
import logging
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect


# ---------------- LOGGING CONFIGURATION ----------------

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Application logging started")


# ---------------- FLASK CONFIGURATION ----------------

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

csrf = CSRFProtect(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")


# ---------------- DATABASE CONNECTION ----------------

def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- ADMIN ACCESS CHECK ----------------

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Admin access required.")
            return redirect(url_for("workspaces"))

        return function(*args, **kwargs)

    return wrapper


# ---------------- CREATE TABLES ----------------

def create_table():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_name TEXT NOT NULL,
            location TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            seat_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT DEFAULT 'Booked',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )
    """)

    # Database migrations

    migrations = {
        "users": [
            ("role", "TEXT NOT NULL DEFAULT 'user'")
        ],
        "workspaces": [
            ("is_active", "INTEGER NOT NULL DEFAULT 1")
        ],
        "seats": [
            ("is_active", "INTEGER NOT NULL DEFAULT 1")
        ]
    }

    for table_name, columns_to_add in migrations.items():

        existing_columns = [
            row["name"]
            for row in cursor.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
        ]

        for column_name, column_definition in columns_to_add:

            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_definition}"
                )

    # Unique seat number within each workspace

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_workspace_seat
        ON seats(workspace_id, seat_number)
    """)

    # Only one active booking per seat

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_seat
        ON bookings(seat_id)
        WHERE status = 'Booked'
    """)

    # Insert sample workspaces if database is empty

    workspace_count = cursor.execute(
        "SELECT COUNT(*) FROM workspaces"
    ).fetchone()[0]

    if workspace_count == 0:

        sample_workspaces = [
            ("Tech Workspace", "Bangalore"),
            ("Training Room", "Belagavi"),
            ("Meeting Room", "Mysore")
        ]

        cursor.executemany("""
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
        """, sample_workspaces)

    # Insert sample seats without duplicates

    workspaces_list = cursor.execute(
        "SELECT id FROM workspaces"
    ).fetchall()

    for workspace in workspaces_list:

        for number in range(1, 6):

            cursor.execute("""
                INSERT OR IGNORE INTO seats
                (workspace_id, seat_number, status)
                VALUES (?, ?, 'Available')
            """, (workspace["id"], f"A{number}"))

    conn.commit()
    conn.close()


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("workspaces"))


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    logging.info("Registration page accessed")

    if request.method == "POST":

        logging.info("Registration form submitted")

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            logging.warning("Registration failed: Empty fields")
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            logging.warning("Registration failed: Invalid email")
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        if len(password) < 6:
            logging.warning("Registration failed: Password too short")
            flash("Password must contain at least 6 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        conn = connect_db()

        try:

            conn.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, 'user')
            """, (name, email, hashed_password))

            conn.commit()

            logging.info("User registration successful")
            flash("Registration successful. Please login.")

        except sqlite3.IntegrityError:

            logging.warning("Registration failed: Duplicate email")
            flash("Email already registered.")

        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")



# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    logging.info("Login page accessed")

    if request.method == "POST":

        logging.info("Login form submitted")

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Input validation
        if not email or not password:
            logging.warning("Login failed: Empty fields")
            flash("Please enter both email and password.")
            return render_template("login.html")

        conn = connect_db()

        try:
            user = conn.execute("""
                SELECT * FROM users WHERE email = ?
            """, (email,)).fetchone()

        except sqlite3.Error:
            logging.exception("Database error during login")
            flash("Something went wrong. Please try again.")
            return render_template("login.html")

        finally:
            conn.close()

        # Check email and password
        if user and check_password_hash(user["password"], password):

            logging.info("User login successful")

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                logging.info("Admin login successful")
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("workspaces"))

        logging.warning("Login failed: Invalid email or password")
        flash("Invalid email or password.")

    return render_template("login.html")



# ---------------- REST API REGISTER ----------------

@app.route("/api/register", methods=["POST"])
def api_register():

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"message": "Please fill all fields."}), 400

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"message": "Invalid email address."}), 400

    if len(password) < 6:
        return jsonify({
            "message": "Password must contain at least 6 characters."
        }), 400

    hashed_password = generate_password_hash(password)
    conn = connect_db()

    try:

        conn.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'user')
        """, (name, email, hashed_password))

        conn.commit()

        return jsonify({
            "message": "Registration successful."
        }), 201

    except sqlite3.IntegrityError:

        return jsonify({
            "message": "Email already registered."
        }), 409

    finally:
        conn.close()


# ---------------- REST API LOGIN ----------------

@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required."
        }), 400

    conn = connect_db()

    user = conn.execute("""
        SELECT * FROM users WHERE email = ?
    """, (email,)).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):

        return jsonify({
            "message": "Login successful.",
            "user_id": user["id"],
            "name": user["name"],
            "role": user["role"]
        }), 200

    return jsonify({
        "message": "Invalid email or password."
    }), 401


# ---------------- LOGOUT ----------------

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()
    return redirect(url_for("login"))

# ---------------- USER DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("workspaces"))


# ==================================================
#                 USER WORKSPACES
# ==================================================

@app.route("/workspaces")
def workspaces():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    search = request.args.get("search", "").strip()
    conn = connect_db()

    workspace_list = conn.execute("""
        SELECT
            w.*,
            COUNT(s.id) AS total_seats,
            COALESCE(SUM(
                CASE WHEN s.status = 'Available'
                THEN 1 ELSE 0 END
            ), 0) AS available_seats,
            COALESCE(SUM(
                CASE WHEN s.status = 'Booked'
                THEN 1 ELSE 0 END
            ), 0) AS booked_seats
        FROM workspaces w
        LEFT JOIN seats s
        ON w.id = s.workspace_id AND s.is_active = 1
        WHERE w.is_active = 1
        AND (
            w.workspace_name LIKE ?
            OR w.location LIKE ?
        )
        GROUP BY w.id
        ORDER BY w.id
    """, (f"%{search}%", f"%{search}%")).fetchall()

    conn.close()

    return render_template(
        "workspaces.html",
        workspaces=workspace_list,
        search=search
    )


# ---------------- WORKSPACE DETAILS ----------------

@app.route("/workspace/<int:workspace_id>")
def workspace_details(workspace_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ? AND is_active = 1
    """, (workspace_id,)).fetchone()

    conn.close()

    if workspace is None:
        flash("Workspace not found or inactive.")
        return redirect(url_for("workspaces"))

    return render_template(
        "workspace_details.html",
        workspace=workspace
    )


# ---------------- DISPLAY SEATS ----------------

@app.route("/workspace/<int:workspace_id>/seats")
def display_seats(workspace_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ? AND is_active = 1
    """, (workspace_id,)).fetchone()

    if workspace is None:
        conn.close()
        flash("Workspace not found or inactive.")
        return redirect(url_for("workspaces"))

    seats = conn.execute("""
        SELECT * FROM seats
        WHERE workspace_id = ? AND is_active = 1
        ORDER BY seat_number
    """, (workspace_id,)).fetchall()

    total_seats = len(seats)

    available_seats = sum(
        1 for seat in seats
        if seat["status"] == "Available"
    )

    booked_seats = sum(
        1 for seat in seats
        if seat["status"] == "Booked"
    )

    conn.close()

    return render_template(
        "seats.html",
        workspace=workspace,
        seats=seats,
        total_seats=total_seats,
        available_seats=available_seats,
        booked_seats=booked_seats
    )


# ---------------- BOOK SEAT ----------------

@app.route("/book-seat/<int:seat_id>", methods=["POST"])
def book_seat(seat_id):

    logging.info("Seat booking request received")
    logging.info("Booking requested for seat ID: %s", seat_id)

    if "user_id" not in session:
        logging.warning("Booking failed: User not logged in")
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        logging.warning("Booking blocked: Admin attempted seat booking")
        return redirect(url_for("admin_dashboard"))

    conn = connect_db()

    try:

        conn.execute("BEGIN IMMEDIATE")

        seat = conn.execute("""
            SELECT s.*, w.is_active AS workspace_active
            FROM seats s
            JOIN workspaces w ON s.workspace_id = w.id
            WHERE s.id = ?
            AND s.is_active = 1
            AND w.is_active = 1
        """, (seat_id,)).fetchone()

        if seat is None:

            conn.rollback()

            logging.warning(
                "Booking failed: Seat ID %s not found or inactive",
                seat_id
            )

            flash("Seat or workspace not found or inactive.")
            return redirect(url_for("workspaces"))

        if seat["status"] != "Available":

            conn.rollback()

            logging.warning(
                "Booking failed: Seat ID %s is already booked",
                seat_id
            )

            flash("This seat is already booked.")

            return redirect(url_for(
                "display_seats",
                workspace_id=seat["workspace_id"]
            ))

        conn.execute("""
            UPDATE seats
            SET status = 'Booked'
            WHERE id = ?
            AND status = 'Available'
            AND is_active = 1
        """, (seat_id,))

        conn.execute("""
            INSERT INTO bookings
            (user_id, seat_id, booking_date, status)
            VALUES (?, ?, ?, 'Booked')
        """, (
            session["user_id"],
            seat_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

        logging.info(
            "Seat booked successfully: seat ID %s, user ID %s",
            seat_id, session["user_id"]
        )

        flash("Seat booked successfully.")

        return redirect(url_for(
            "display_seats",
            workspace_id=seat["workspace_id"]
        ))

    except sqlite3.IntegrityError:

        conn.rollback()

        logging.warning(
            "Booking failed due to database integrity error for seat ID %s",
            seat_id
        )

        flash("This seat is already booked.")

        seat = conn.execute("""
            SELECT workspace_id FROM seats WHERE id = ?
        """, (seat_id,)).fetchone()

        if seat:

            return redirect(url_for(
                "display_seats",
                workspace_id=seat["workspace_id"]
            ))

        return redirect(url_for("workspaces"))

    except Exception:

        conn.rollback()

        logging.exception(
            "Unexpected error while booking seat ID %s",
            seat_id
        )

        flash("An error occurred while booking the seat.")
        return redirect(url_for("workspaces"))

    finally:
        conn.close()


# ---------------- MY BOOKINGS ----------------

@app.route("/my-bookings")
def my_bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))


    conn = connect_db()

    bookings = conn.execute("""
        SELECT
            b.id AS booking_id,
            b.booking_date,
            b.status,
            s.seat_number,
            w.workspace_name,
            w.location
        FROM bookings b
        JOIN seats s ON b.seat_id = s.id
        JOIN workspaces w ON s.workspace_id = w.id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )


# ---------------- CANCEL BOOKING ----------------

@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))


    conn = connect_db()

    try:

        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute("""
            SELECT * FROM bookings
            WHERE id = ?
            AND user_id = ?
            AND status = 'Booked'
        """, (booking_id, session["user_id"])).fetchone()

        if booking is None:

            conn.rollback()
            flash("Booking not found or already cancelled.")
            return redirect(url_for("my_bookings"))

        conn.execute("""
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE id = ?
        """, (booking_id,))

        conn.execute("""
            UPDATE seats
            SET status = 'Available'
            WHERE id = ?
        """, (booking["seat_id"],))

        conn.commit()
        flash("Booking cancelled successfully.")

    except sqlite3.Error:

        conn.rollback()
        logging.exception("Error while cancelling booking %s", booking_id)
        flash("Unable to cancel booking.")

    finally:
        conn.close()

    return redirect(url_for("my_bookings"))


# ==================================================
#                    ADMIN MODULE
# ==================================================


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = connect_db()

    total_workspaces = conn.execute("""
        SELECT COUNT(*) FROM workspaces
        WHERE is_active = 1
    """).fetchone()[0]

    total_seats = conn.execute("""
        SELECT COUNT(*) FROM seats
        WHERE is_active = 1
    """).fetchone()[0]

    total_users = conn.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'user'
    """).fetchone()[0]

    total_bookings = conn.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE status = 'Booked'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_workspaces=total_workspaces,
        total_seats=total_seats,
        total_users=total_users,
        total_bookings=total_bookings
    )


# ---------------- ADMIN WORKSPACE LIST / CREATE ----------------

@app.route("/admin/workspaces", methods=["GET", "POST"])
@admin_required
def admin_workspaces():

    conn = connect_db()

    if request.method == "POST":

        workspace_name = request.form.get(
            "workspace_name", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        if not workspace_name or not location:

            conn.close()
            flash("Please enter workspace name and location.")

            return redirect(url_for("admin_workspaces"))

        conn.execute("""
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
        """, (workspace_name, location))

        conn.commit()
        conn.close()

        flash("Workspace added successfully.")
        return redirect(url_for("admin_workspaces"))

    workspace_list = conn.execute("""
        SELECT * FROM workspaces
        WHERE is_active = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_workspaces.html",
        workspaces=workspace_list
    )


# ---------------- ADMIN UPDATE WORKSPACE ----------------

@app.route(
    "/admin/workspace/update/<int:workspace_id>",
    methods=["POST"]
)
@admin_required
def admin_update_workspace(workspace_id):

    workspace_name = request.form.get(
        "workspace_name", ""
    ).strip()

    location = request.form.get(
        "location", ""
    ).strip()

    if not workspace_name or not location:

        flash("Please fill all workspace fields.")
        return redirect(url_for("admin_workspaces"))

    conn = connect_db()

    cursor = conn.execute("""
        UPDATE workspaces
        SET workspace_name = ?, location = ?
        WHERE id = ? AND is_active = 1
    """, (workspace_name, location, workspace_id))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        flash("Active workspace not found.")
    else:
        flash("Workspace updated successfully.")

    return redirect(url_for("admin_workspaces"))


# ---------------- ADMIN DEACTIVATE WORKSPACE ----------------

@app.route(
    "/admin/workspace/deactivate/<int:workspace_id>",
    methods=["POST"]
)
@admin_required
def admin_deactivate_workspace(workspace_id):

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ? AND is_active = 1
    """, (workspace_id,)).fetchone()

    if workspace is None:

        conn.close()
        flash("Workspace not found or already inactive.")

        return redirect(url_for("admin_workspaces"))

    active_booking = conn.execute("""
        SELECT COUNT(*)
        FROM bookings b
        JOIN seats s ON b.seat_id = s.id
        WHERE s.workspace_id = ?
        AND b.status = 'Booked'
    """, (workspace_id,)).fetchone()[0]

    if active_booking > 0:

        conn.close()
        flash("Cannot deactivate workspace. It has active bookings.")

        return redirect(url_for("admin_workspaces"))

    cursor = conn.execute("""
        UPDATE workspaces
        SET is_active = 0
        WHERE id = ? AND is_active = 1
    """, (workspace_id,))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        flash("Workspace could not be deactivated.")
    else:
        flash("Workspace deactivated successfully.")

    return redirect(url_for("admin_workspaces"))


# ---------------- ADMIN SEAT LIST / CREATE ----------------

@app.route(
    "/admin/workspace/<int:workspace_id>/seats",
    methods=["GET", "POST"]
)
@admin_required
def admin_seats(workspace_id):

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ?
    """, (workspace_id,)).fetchone()

    if workspace is None:

        conn.close()
        flash("Workspace not found.")
        return redirect(url_for("admin_workspaces"))

    if request.method == "POST":

        if workspace["is_active"] != 1:

            conn.close()
            flash("Cannot add seats to an inactive workspace.")

            return redirect(url_for("admin_workspaces"))

        seat_number = request.form.get(
            "seat_number", ""
        ).strip().upper()

        if not seat_number:

            conn.close()
            flash("Please enter a seat number.")

            return redirect(url_for(
                "admin_seats",
                workspace_id=workspace_id
            ))

        try:

            conn.execute("""
                INSERT INTO seats
                (workspace_id, seat_number, status, is_active)
                VALUES (?, ?, 'Available', 1)
            """, (workspace_id, seat_number))

            conn.commit()
            flash("Seat added successfully.")

        except sqlite3.IntegrityError:

            flash("This seat number already exists in this workspace.")

        finally:
            conn.close()

        return redirect(url_for(
            "admin_seats",
            workspace_id=workspace_id
        ))

    seats = conn.execute("""
        SELECT * FROM seats
        WHERE workspace_id = ?
        AND is_active = 1
        ORDER BY seat_number
    """, (workspace_id,)).fetchall()

    conn.close()

    return render_template(
        "admin_seats.html",
        workspace=workspace,
        seats=seats
    )


# ---------------- ADMIN UPDATE SEAT ----------------

@app.route(
    "/admin/seat/update/<int:seat_id>",
    methods=["POST"]
)
@admin_required
def admin_update_seat(seat_id):

    conn = connect_db()

    seat = conn.execute("""
        SELECT * FROM seats WHERE id = ?
    """, (seat_id,)).fetchone()

    if seat is None:

        conn.close()
        flash("Seat not found.")
        return redirect(url_for("admin_workspaces"))

    if seat["is_active"] != 1:

        conn.close()
        flash("Cannot update an inactive seat.")

        return redirect(url_for(
            "admin_seats",
            workspace_id=seat["workspace_id"]
        ))

    if seat["status"] == "Booked":

        conn.close()
        flash("Cannot update a booked seat.")

        return redirect(url_for(
            "admin_seats",
            workspace_id=seat["workspace_id"]
        ))

    seat_number = request.form.get(
        "seat_number", ""
    ).strip().upper()

    if not seat_number:

        conn.close()
        flash("Please enter a seat number.")

        return redirect(url_for(
            "admin_seats",
            workspace_id=seat["workspace_id"]
        ))

    try:

        cursor = conn.execute("""
            UPDATE seats
            SET seat_number = ?
            WHERE id = ?
            AND is_active = 1
            AND status = 'Available'
        """, (seat_number, seat_id))

        conn.commit()

        if cursor.rowcount == 0:
            flash("Seat could not be updated.")
        else:
            flash("Seat updated successfully.")

    except sqlite3.IntegrityError:

        flash("This seat number already exists in the workspace.")

    finally:
        conn.close()

    return redirect(url_for(
        "admin_seats",
        workspace_id=seat["workspace_id"]
    ))


# ---------------- ADMIN DEACTIVATE SEAT ----------------

@app.route(
    "/admin/seat/deactivate/<int:seat_id>",
    methods=["POST"]
)
@admin_required
def admin_deactivate_seat(seat_id):

    conn = connect_db()

    seat = conn.execute("""
        SELECT * FROM seats WHERE id = ?
    """, (seat_id,)).fetchone()

    if seat is None:

        conn.close()
        flash("Seat not found.")
        return redirect(url_for("admin_workspaces"))

    if seat["is_active"] != 1:

        conn.close()
        flash("This seat is already inactive.")

        return redirect(url_for(
            "admin_seats",
            workspace_id=seat["workspace_id"]
        ))

    if seat["status"] == "Booked":

        conn.close()
        flash("Cannot deactivate a booked seat.")

        return redirect(url_for(
            "admin_seats",
            workspace_id=seat["workspace_id"]
        ))

    conn.execute("""
        UPDATE seats
        SET is_active = 0
        WHERE id = ?
        AND is_active = 1
        AND status = 'Available'
    """, (seat_id,))

    conn.commit()
    conn.close()

    flash("Seat deactivated successfully.")

    return redirect(url_for(
        "admin_seats",
        workspace_id=seat["workspace_id"]
    ))
# ---------------- ERROR HANDLING ----------------

@app.errorhandler(404)
def page_not_found(error):
    logging.warning("404 Error: Page not found")
    return "Page not found. Please check the URL.", 404

@app.errorhandler(500)
def internal_server_error(error):
    logging.exception("500 Error: Internal server error")
    return "Something went wrong. Please try again later.", 500


# ---------------- RUN APPLICATION ----------------
print(app.url_map)
if __name__ == "__main__":

    create_table()

    print("Database created successfully")
    print("Starting Flask server...")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )