
import sqlite3


conn = sqlite3.connect("day4.db")


conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    password TEXT
)
""")


conn.execute("""
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_name TEXT,
    location TEXT
)
""")


conn.execute("""
CREATE TABLE IF NOT EXISTS seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    seat_number TEXT,
    status TEXT,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
)
""")


conn.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    seat_id INTEGER,
    booking_date TEXT,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (seat_id) REFERENCES seats(id)
)
""")

conn.commit()
conn.close()

print("All four tables created successfully!")

import sqlite3

conn = sqlite3.connect("day4.db")

conn.execute(
    "INSERT INTO workspaces (workspace_name, location) VALUES (?, ?)",
    ("Tech Workspace", "Bangalore")
)
print("Workspace added successfully!")

conn.execute(
    "INSERT INTO seats (workspace_id, seat_number, status) VALUES (?, ?, ?)",
    (1, "A1", "Available")
)
print("Seat added successfully!")

conn.execute(
    "INSERT INTO bookings (user_id, seat_id, booking_date, status) VALUES (?, ?, ?, ?)",
    (1, 1, "2026-11-05", "Confirmed")
)
print("Booking added successfully!")

conn.commit()
conn.close()


conn = sqlite3.connect("day4.db")

print("\n--- USERS ---")
users = conn.execute("SELECT * FROM users").fetchall()
for user in users:
    print(user)


print("\n--- WORKSPACES ---")
workspaces = conn.execute("SELECT * FROM workspaces").fetchall()
for workspace in workspaces:
    print(workspace)


print("\n--- SEATS ---")
seats = conn.execute("SELECT * FROM seats").fetchall()
for seat in seats:
    print(seat)


print("\n--- BOOKINGS ---")
bookings = conn.execute("SELECT * FROM bookings").fetchall()
for booking in bookings:
    print(booking)

conn.close()


conn = sqlite3.connect("day4.db")

conn.execute(
    "UPDATE users SET name = ? WHERE id = ?",
    ("Rahul Kumar", 1)
)


conn.execute(
    "UPDATE workspaces SET location = ? WHERE id = ?",
    ("Mysore", 1)
)


conn.execute(
    "UPDATE seats SET status = ? WHERE id = ?",
    ("Booked", 1)
)


conn.execute(
    "UPDATE bookings SET status = ? WHERE id = ?",
    ("Cancelled", 1)
)

conn.commit()
conn.close()

print("\nAll records updated successfully!")


conn = sqlite3.connect("day4.db")


conn.execute("DELETE FROM bookings WHERE id = ?", (1,))


conn.execute("DELETE FROM seats WHERE id = ?", (1,))


conn.execute("DELETE FROM users WHERE id = ?", (1,))

conn.execute("DELETE FROM workspaces WHERE id = ?", (1,))

conn.commit()
conn.close()

print("\nAll records deleted successfully!")

import sqlite3

conn = sqlite3.connect("day4.db")

conn.execute("DELETE FROM bookings")
conn.execute("DELETE FROM seats")
conn.execute("DELETE FROM users")
conn.execute("DELETE FROM workspaces")

conn.commit()
conn.close()

print("All records deleted successfully!")
import sqlite3

conn = sqlite3.connect("day4.db")

print("USERS:", conn.execute("SELECT * FROM users").fetchall())
print("WORKSPACES:", conn.execute("SELECT * FROM workspaces").fetchall())
print("SEATS:", conn.execute("SELECT * FROM seats").fetchall())
print("BOOKINGS:", conn.execute("SELECT * FROM bookings").fetchall())

conn.close()
import sqlite3

conn = sqlite3.connect("day4.db")

print("USERS:", conn.execute("SELECT * FROM users").fetchall())

print("WORKSPACES:", conn.execute("SELECT * FROM workspaces").fetchall())

print("SEATS:", conn.execute("SELECT * FROM seats").fetchall())

print("BOOKINGS:", conn.execute("SELECT * FROM bookings").fetchall())

conn.close()

