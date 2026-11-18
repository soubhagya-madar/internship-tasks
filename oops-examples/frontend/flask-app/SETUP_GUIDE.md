# Book My Seat – Setup Guide

## 1. About the Project

Book My Seat is a web application where users can view available workspaces and book seats.

Users can register, log in, view their bookings, and cancel bookings. Admins can add and manage workspaces and seats.

The project is developed using Python Flask and SQLite.

## 2. Technologies Used

- Python
- Flask
- HTML
- CSS
- SQLite
- Flask-WTF

## 3. Requirements

Before running the project, make sure the following are installed:

- Python 3
- Visual Studio Code
- Required Python packages

## 4. How to Set Up the Project

### Step 1: Open the Project

Open VS Code and select the `flask-app` project folder.

### Step 2: Open the Terminal

Go to Terminal → New Terminal in VS Code.

### Step 3: Install the Required Packages

Run this command:

```bash
pip install Flask Flask-WTF
```

### Step 4: Set the Secret Key

In the PowerShell terminal, run:

```powershell
$env:FLASK_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 5: Run the Application

Run the following command:

```bash
python app.py
```

### Step 6: Open the Application

After starting the application, open your browser and enter:

`http://127.0.0.1:5000/`

The application will open in your browser.

## 5. Database

The project uses SQLite to store the application details.

The database contains four main tables:

- Users
- Workspaces
- Seats
- Bookings

The tables are created by the application when the database setup function runs.

## 6. Main Features

- User registration and login
- View available workspaces
- Check seat availability
- Book a seat
- View booking details
- Cancel a booking
- Admin dashboard
- Manage workspaces and seats

## 7. Security

Some basic security features are included in the project:

- Password hashing
- CSRF protection
- Parameterized SQL queries
- Admin access control
- Secret key configuration using an environment variable

## 8. Conclusion

This guide explains how to install, configure, and run the Book My Seat application locally. It also provides an overview of the technologies and main features used in the project.