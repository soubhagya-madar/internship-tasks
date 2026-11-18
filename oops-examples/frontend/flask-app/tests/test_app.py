
import unittest
import tempfile
import os
import app as app_module


class TestBookMySeat(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary database for testing
        cls.temp_dir = tempfile.TemporaryDirectory()

        app_module.DATABASE = os.path.join(
            cls.temp_dir.name, "test_users.db"
        )

        app_module.create_table()
        app_module.app.config["TESTING"] = True
        app_module.app.config["WTF_CSRF_ENABLED"] = False

    def setUp(self):
        self.client = app_module.app.test_client()

    # ---------------- REGISTRATION TESTS ----------------

    # Test 1: Login page
    def test_login_page(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    # Test 2: Valid user registration
    def test_user_registration(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Test User",
                "email": "testuser@example.com",
                "password": "test123"
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)

    # Test 3: Invalid email registration
    def test_invalid_email(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Test User",
                "email": "invalidemail",
                "password": "test123"
            },
            follow_redirects=True
        )

        self.assertIn(
            b"Please enter a valid email address.",
            response.data
        )

    # Test 4: Short password registration
    def test_short_password(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Test User",
                "email": "short@example.com",
                "password": "123"
            },
            follow_redirects=True
        )

        self.assertIn(
            b"Password must contain at least 6 characters.",
            response.data
        )

    # Test 5: Empty registration fields
    def test_empty_registration(self):
        response = self.client.post(
            "/register",
            data={
                "name": "",
                "email": "",
                "password": ""
            },
            follow_redirects=True
        )

        self.assertIn(
            b"Please fill all fields.",
            response.data
        )

    # ---------------- HELPER METHODS ----------------

    # Helper method to create or get a test user
    def create_test_user(
        self,
        email="login@example.com",
        name="Login User"
    ):
        password_hash = app_module.generate_password_hash("test123")

        conn = app_module.connect_db()

        try:
            conn.execute("""
                INSERT OR IGNORE INTO users
                (name, email, password, role)
                VALUES (?, ?, ?, 'user')
            """, (name, email, password_hash))

            conn.commit()

            user = conn.execute("""
                SELECT id FROM users
                WHERE email = ?
            """, (email,)).fetchone()

            return user["id"]

        finally:
            conn.close()

    # Helper method to create a test seat
    def create_test_seat(self, status="Available"):
        conn = app_module.connect_db()

        try:
            workspace = conn.execute("""
                SELECT id FROM workspaces
                WHERE is_active = 1
                LIMIT 1
            """).fetchone()

            if workspace is None:
                cursor = conn.execute("""
                    INSERT INTO workspaces
                    (workspace_name, location, is_active)
                    VALUES (?, ?, 1)
                """, ("Test Workspace", "Bangalore"))

                workspace_id = cursor.lastrowid

            else:
                workspace_id = workspace["id"]

            seat_number = "TEST-" + os.urandom(4).hex()

            cursor = conn.execute("""
                INSERT INTO seats
                (workspace_id, seat_number, status, is_active)
                VALUES (?, ?, ?, 1)
            """, (workspace_id, seat_number, status))

            seat_id = cursor.lastrowid

            conn.commit()

            return seat_id, workspace_id

        finally:
            conn.close()

    # Helper method to create a test booking
    def create_test_booking(
        self,
        user_id=None,
        booking_status="Booked"
    ):
        if user_id is None:
            user_id = self.create_test_user()

        seat_id, workspace_id = self.create_test_seat("Booked")

        conn = app_module.connect_db()

        try:
            cursor = conn.execute("""
                INSERT INTO bookings
                (user_id, seat_id, booking_date, status)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                seat_id,
                "2026-11-18 12:00:00",
                booking_status
            ))

            booking_id = cursor.lastrowid

            conn.commit()

            return booking_id, seat_id, workspace_id

        finally:
            conn.close()

    # ---------------- LOGIN TESTS ----------------

    # Test 6: Login with correct credentials
    def test_valid_login(self):
        self.create_test_user()

        response = self.client.post(
            "/login",
            data={
                "email": "login@example.com",
                "password": "test123"
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/workspaces", response.location)

    # Test 7: Login with incorrect password
    def test_invalid_password(self):
        self.create_test_user()

        response = self.client.post(
            "/login",
            data={
                "email": "login@example.com",
                "password": "wrong123"
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            b"Invalid email or password.",
            response.data
        )

    # Test 8: Login with unregistered email
    def test_unregistered_email(self):
        response = self.client.post(
            "/login",
            data={
                "email": "unknown@example.com",
                "password": "test123"
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            b"Invalid email or password.",
            response.data
        )

    # ---------------- WORKSPACE TESTS ----------------

    # Test 9: Workspaces page without login
    def test_workspaces_without_login(self):
        response = self.client.get("/workspaces")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 10: Normal user can view workspaces
    def test_workspaces_for_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Test User"
            session["role"] = "user"

        response = self.client.get("/workspaces")

        self.assertEqual(response.status_code, 200)

    # Test 11: Admin redirected from workspaces
    def test_workspaces_for_admin(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["user_name"] = "Test Admin"
            session["role"] = "admin"

        response = self.client.get("/workspaces")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.location)

    # Test 12: Workspace details without login
    def test_workspace_details_without_login(self):
        response = self.client.get("/workspace/1")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 13: Workspace details for logged-in user
    def test_workspace_details_for_user(self):
        conn = app_module.connect_db()

        try:
            workspace = conn.execute("""
                SELECT id FROM workspaces
                WHERE is_active = 1
                LIMIT 1
            """).fetchone()

        finally:
            conn.close()

        self.assertIsNotNone(workspace)

        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = "user"

        response = self.client.get(
            f"/workspace/{workspace['id']}"
        )

        self.assertEqual(response.status_code, 200)

    # Test 14: Invalid workspace details
    def test_invalid_workspace_details(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = "user"

        response = self.client.get(
            "/workspace/99999",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/workspaces", response.location)

    # ---------------- DISPLAY SEATS TESTS ----------------

    # Test 15: Display seats without login
    def test_display_seats_without_login(self):
        response = self.client.get("/workspace/1/seats")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 16: Display seats for logged-in user
    def test_display_seats_for_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = "user"

        response = self.client.get("/workspace/1/seats")

        self.assertEqual(response.status_code, 200)

    # Test 17: Display seats for invalid workspace
    def test_display_seats_invalid_workspace(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = "user"

        response = self.client.get(
            "/workspace/99999/seats",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/workspaces", response.location)

    # ---------------- BOOKING TESTS ----------------

    # Test 18: Booking without login
    def test_booking_without_login(self):
        response = self.client.post("/book-seat/1")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 19: Admin cannot book a seat
    def test_admin_cannot_book_seat(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["role"] = "admin"

        response = self.client.post("/book-seat/1")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.location)

    # Test 20: Successful seat booking
    def test_successful_seat_booking(self):
        user_id = self.create_test_user()
        seat_id, workspace_id = self.create_test_seat()

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.post(
            f"/book-seat/{seat_id}",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            f"/workspace/{workspace_id}/seats",
            response.location
        )

        conn = app_module.connect_db()

        try:
            seat = conn.execute("""
                SELECT status FROM seats WHERE id = ?
            """, (seat_id,)).fetchone()

            booking = conn.execute("""
                SELECT * FROM bookings
                WHERE seat_id = ? AND user_id = ?
            """, (seat_id, user_id)).fetchone()

            self.assertEqual(seat["status"], "Booked")
            self.assertIsNotNone(booking)

        finally:
            conn.close()

    # Test 21: Booking an already booked seat
    def test_booking_already_booked_seat(self):
        user_id = self.create_test_user()
        seat_id, workspace_id = self.create_test_seat("Booked")

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.post(
            f"/book-seat/{seat_id}",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            f"/workspace/{workspace_id}/seats",
            response.location
        )

    # Test 22: Booking an invalid seat
    def test_booking_invalid_seat(self):
        user_id = self.create_test_user()

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.post(
            "/book-seat/99999",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/workspaces", response.location)

    # ---------------- MY BOOKINGS TESTS ----------------

    # Test 23: View bookings without login
    def test_my_bookings_without_login(self):
        response = self.client.get("/my-bookings")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 24: View bookings after login
    def test_my_bookings_for_user(self):
        user_id = self.create_test_user()
        self.create_test_booking(user_id)

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.get("/my-bookings")

        self.assertEqual(response.status_code, 200)

    # ---------------- CANCEL BOOKING TESTS ----------------

    # Test 25: Cancel booking without login
    def test_cancel_booking_without_login(self):
        response = self.client.post("/cancel-booking/1")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    # Test 26: Successfully cancel a booking
    def test_successful_booking_cancellation(self):
        user_id = self.create_test_user()
        booking_id, seat_id, workspace_id = (
            self.create_test_booking(user_id)
        )

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.post(
            f"/cancel-booking/{booking_id}",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/my-bookings", response.location)

        conn = app_module.connect_db()

        try:
            booking = conn.execute("""
                SELECT status FROM bookings WHERE id = ?
            """, (booking_id,)).fetchone()

            seat = conn.execute("""
                SELECT status FROM seats WHERE id = ?
            """, (seat_id,)).fetchone()

            self.assertEqual(booking["status"], "Cancelled")
            self.assertEqual(seat["status"], "Available")

        finally:
            conn.close()

    # Test 27: Cancel an already cancelled booking
    def test_cancel_already_cancelled_booking(self):
        user_id = self.create_test_user()

        booking_id, seat_id, workspace_id = (
            self.create_test_booking(
                user_id,
                booking_status="Cancelled"
            )
        )

        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = "user"

        response = self.client.post(
            f"/cancel-booking/{booking_id}",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/my-bookings", response.location)

    # Test 28: User cannot cancel another user's booking
    def test_user_cannot_cancel_other_users_booking(self):
        other_user_id = self.create_test_user(
            email="other@example.com",
            name="Other User"
        )

        booking_id, seat_id, workspace_id = (
            self.create_test_booking(other_user_id)
        )

        current_user_id = self.create_test_user()

        with self.client.session_transaction() as session:
            session["user_id"] = current_user_id
            session["role"] = "user"

        response = self.client.post(
            f"/cancel-booking/{booking_id}",
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/my-bookings", response.location)

        conn = app_module.connect_db()

        try:
            booking = conn.execute("""
                SELECT status FROM bookings WHERE id = ?
            """, (booking_id,)).fetchone()

            seat = conn.execute("""
                SELECT status FROM seats WHERE id = ?
            """, (seat_id,)).fetchone()

            self.assertEqual(booking["status"], "Booked")
            self.assertEqual(seat["status"], "Booked")

        finally:
            conn.close()

    # ---------------- CLEANUP ----------------

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
