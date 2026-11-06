
from flask import Flask, request, session, redirect
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for session security
app.secret_key = "change_this_to_a_random_secret_key"


# Database connection
def connect_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create users table
def create_table():
    conn = connect_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    return "Welcome to my application"


# User registration
@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    # Input validation
    if not name or not email or not password:
        return "All fields are required"

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "Please enter a valid email"

    if len(password) < 6:
        return "Password must contain at least 6 characters"

    conn = connect_db()

    # Check duplicate email
    user = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if user:
        conn.close()
        return "Email already registered"

    # Hash the password
    hashed_password = generate_password_hash(password)

    conn.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, hashed_password)
    )

    conn.commit()
    conn.close()

    return "Registration successful"


# User login
@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    # Input validation
    if not email or not password:
        return "Email and password are required"

    conn = connect_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):

        session.clear()

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]

        return redirect("/dashboard")

    else:
        return "Invalid email or password"


# Protected dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return "Please login first", 401

    return "Welcome " + session["user_name"] + "! You are logged in."


# User logout
@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return "Logout successful"


# Run application
if __name__ == "__main__":
    create_table()
    app.run(debug=True)
