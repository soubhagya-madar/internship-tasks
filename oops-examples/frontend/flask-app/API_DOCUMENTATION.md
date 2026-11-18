# Book My Seat – API Documentation

## 1. Introduction

This document explains the APIs used in the Book My Seat project.

The application has two APIs: one for user registration and another for user login. These APIs are developed using Python and Flask and connected to the SQLite database.

## 2. Technologies Used

- Python
- Flask
- SQLite
- Postman
- HTML and CSS

## 3. Application URL

The application runs locally at:

`http://127.0.0.1:5000`

## 4. Registration API

**URL:** `/api/register`

**Method:** POST

**Purpose:** This API is used to create a new user account.

**Input:**

```json
{
    "name": "Soubhagya",
    "email": "user@example.com",
    "password": "password123"
}
```

**Expected Result:**

If the details are valid, a new user account is created and a success message is returned.

**Possible Errors:**
- 400 – Invalid or missing details.
- 409 – Email already registered.

## 5. Login API

**URL:** `/api/login`

**Method:** POST

**Purpose:** This API checks whether the entered email and password are correct.

**Input:**

```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Expected Result:**

If the login details are correct, the API returns the user's ID, name, and role along with a success message.

**Possible Errors:**
- 400 – Email or password is missing.
- 401 – Incorrect login details.

**Note:** This API checks the credentials but does not create a web login session.

## 6. Testing Using Postman

I used Postman to test the registration and login APIs.

The following steps are used:

1. Open Postman.
2. Select the POST method.
3. Enter the API URL.
4. Select Body and choose raw JSON.
5. Enter the required details.
6. Click Send and check the response.

The APIs return success or error messages based on the entered details.

## 7. Database Details

The application uses SQLite to store information.

The main database tables are:

- **Users:** Stores user registration details.
- **Workspaces:** Stores workspace information.
- **Seats:** Stores seat details and availability.
- **Bookings:** Stores booking details and status.

## 8. Security

The application includes some basic security measures:

- Passwords are stored in hashed format.
- SQL queries use parameters.
- CSRF protection is enabled for POST requests.
- Admin pages have role-based access.
- The Flask secret key is configured using an environment variable.

## 9. Conclusion

The registration and login APIs help users create accounts and verify their login details. Postman is used to test these APIs and check their responses.

This documentation explains how the APIs work and how they are tested.