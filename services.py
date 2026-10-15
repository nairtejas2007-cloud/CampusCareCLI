from contextlib import contextmanager
from datetime import datetime
from os import getenv

import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection
from models import Admin, Complaint, Faculty, Student


def faculty_email_matches_institute_domain(email):
    """Check an optional institute email domain configured in the environment."""
    required_domain = getenv("FACULTY_EMAIL_DOMAIN", "").strip().lower().lstrip("@")
    return not required_domain or email.rpartition("@")[2] == required_domain


@contextmanager
def database_cursor(commit=False):
    """Open and reliably close one database connection and cursor."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


class ComplaintManagementSystem:
    """Coordinates account, complaint, assignment, history, and feedback work."""

    def user_from_row(self, row):
        match row["role"]:
            case "student":
                return Student(row["user_id"], row["name"], row["email"], row["role"], row["department_id"])
            case "faculty":
                return Faculty(row["user_id"], row["name"], row["email"], row["role"], row["department_id"])
            case "admin":
                return Admin(row["user_id"], row["name"], row["email"], row["role"], row["department_id"])
            case _:
                raise ValueError("This account has an unsupported role.")

    def get_user(self, user_id):
        with database_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
        return self.user_from_row(row) if row else None

    def register_student(self, name, email, password):
        name = name.strip()
        email = email.strip().lower()
        if not name or len(name) > 100:
            raise ValueError("Enter a name with no more than 100 characters.")
        if "@" not in email or len(email) > 255:
            raise ValueError("Enter a valid email address.")
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise ValueError("An account with that email already exists.")
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'student')",
                (name, email, generate_password_hash(password)),
            )
        return True

    def authenticate_user(self, email, password):
        with database_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
            row = cursor.fetchone()
        if row and row["role"] == "faculty" and not faculty_email_matches_institute_domain(row["email"]):
            return None
        if row and check_password_hash(row["password_hash"], password):
            return self.user_from_row(row)
        return None

    def get_categories(self):
        with database_cursor() as cursor:
            cursor.execute(
                """SELECT category_id, category_name, default_department_id
                   FROM complaint_categories ORDER BY category_name"""
            )
            return cursor.fetchall()

    def get_departments(self):
        with database_cursor() as cursor:
            cursor.execute(
                "SELECT department_id, department_name FROM departments ORDER BY department_name"
            )
            return cursor.fetchall()

    def get_complaints(self, user):
        query = (
            "SELECT c.*, cc.category_name, d.department_name, u.name AS student_name "
            "FROM complaints c "
            "JOIN complaint_categories cc ON cc.category_id = c.category_id "
            "JOIN users u ON u.user_id = c.student_id "
            "LEFT JOIN departments d ON d.department_id = c.assigned_department_id"
        )
        parameters = ()
        if isinstance(user, Student):
            query += " WHERE c.student_id = %s"
            parameters = (user.user_id,)
        elif isinstance(user, Faculty):
            query += " WHERE c.assigned_department_id = %s"
            parameters = (user.department_id,)
        query += " ORDER BY c.created_at DESC"
        with database_cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
        return [row for row in rows if user.can_view_complaint(Complaint(row))]

    def get_complaint_details(self, user, complaint_id):
        query = """SELECT c.*, cc.category_name, d.department_name,
                          student.name AS student_name
                   FROM complaints c
                   JOIN complaint_categories cc ON cc.category_id = c.category_id
                   JOIN users student ON student.user_id = c.student_id
                   LEFT JOIN departments d ON d.department_id = c.assigned_department_id
                   WHERE c.complaint_id = %s"""
        with database_cursor() as cursor:
            cursor.execute(query, (complaint_id,))
            complaint = cursor.fetchone()
            if not complaint or not user.can_view_complaint(Complaint(complaint)):
                return None
            cursor.execute(
                """SELECT cu.*, u.name AS updated_by_name
                   FROM complaint_updates cu JOIN users u ON u.user_id = cu.updated_by
                   WHERE cu.complaint_id = %s ORDER BY cu.updated_at, cu.update_id""",
                (complaint_id,),
            )
            complaint["history"] = cursor.fetchall()
            cursor.execute("SELECT * FROM feedback WHERE complaint_id = %s", (complaint_id,))
            complaint["feedback"] = cursor.fetchone()
        return complaint

    def create_complaint(self, student, form):
        title = form.get("title", "").strip()
        description = form.get("description", "").strip()
        location = form.get("location", "").strip()
        priority = form.get("priority", "Normal")
        try:
            category_id = int(form.get("category_id", ""))
        except (TypeError, ValueError):
            raise ValueError("Choose a complaint category.")
        if not title or len(title) > 150:
            raise ValueError("Enter a title with no more than 150 characters.")
        if not description:
            raise ValueError("The description cannot be empty.")
        if len(description.split()) > 500:
            raise ValueError("The description must be 500 words or fewer.")
        if len(location) > 200:
            raise ValueError("Location must be no more than 200 characters.")
        if priority not in {"Low", "Normal", "High"}:
            raise ValueError("Choose a valid priority.")
        with database_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT default_department_id FROM complaint_categories WHERE category_id = %s",
                (category_id,),
            )
            category = cursor.fetchone()
            if not category:
                raise ValueError("Choose a valid complaint category.")
            cursor.execute(
                """INSERT INTO complaints
                   (student_id, category_id, assigned_department_id, title,
                    description, location, priority)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    student.user_id,
                    category_id,
                    category["default_department_id"],
                    title,
                    description,
                    location or None,
                    priority,
                ),
            )
            complaint_id = cursor.lastrowid
            cursor.execute(
                """INSERT INTO complaint_updates
                   (complaint_id, updated_by, old_status, new_status, remarks)
                   VALUES (%s, %s, NULL, 'Submitted', 'Complaint submitted by student.')""",
                (complaint_id, student.user_id),
            )
        return complaint_id

    def update_complaint_status(self, user, complaint_id, new_status, remarks):
        if not isinstance(user, (Faculty, Admin)):
            raise PermissionError("Only faculty or administrators may update status.")
        remarks = remarks.strip()
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT * FROM complaints WHERE complaint_id = %s", (complaint_id,))
            row = cursor.fetchone()
            if not row or not user.can_view_complaint(Complaint(row)):
                raise PermissionError("You cannot access this complaint.")
            complaint = Complaint(row)
            old_status = complaint.update_status(new_status, remarks)
            cursor.execute(
                """UPDATE complaints SET status = %s,
                   resolved_at = CASE WHEN %s = 'Resolved' THEN %s ELSE resolved_at END
                   WHERE complaint_id = %s""",
                (new_status, new_status, datetime.now(), complaint_id),
            )
            cursor.execute(
                """INSERT INTO complaint_updates
                   (complaint_id, updated_by, old_status, new_status, remarks)
                   VALUES (%s, %s, %s, %s, %s)""",
                (complaint_id, user.user_id, old_status, new_status, remarks or None),
            )

    def assign_complaint(self, admin, complaint_id, department_id):
        if not isinstance(admin, Admin):
            raise PermissionError("Only administrators may assign complaints.")
        department_id = int(department_id) if department_id else None
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT * FROM complaints WHERE complaint_id = %s", (complaint_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Complaint not found.")
            if department_id is not None:
                cursor.execute("SELECT department_id FROM departments WHERE department_id = %s", (department_id,))
                if not cursor.fetchone():
                    raise ValueError("Choose a valid department.")
            staff_id = (
                row["assigned_staff_id"]
                if row["assigned_department_id"] == department_id
                else None
            )
            cursor.execute(
                "UPDATE complaints SET assigned_department_id = %s, assigned_staff_id = %s WHERE complaint_id = %s",
                (department_id, staff_id, complaint_id),
            )
            department_label = str(department_id) if department_id else "awaiting manual assignment"
            remarks = "Administrator assigned department " + department_label
            cursor.execute(
                """INSERT INTO complaint_updates
                   (complaint_id, updated_by, old_status, new_status, remarks)
                   VALUES (%s, %s, %s, %s, %s)""",
                (complaint_id, admin.user_id, row["status"], row["status"], remarks),
            )

    def submit_feedback(self, student, complaint_id, rating, issue_fixed, comments):
        if not isinstance(student, Student):
            raise PermissionError("Only the student who submitted the complaint may give feedback.")
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise ValueError("Choose a rating from 1 to 5.")
        if rating not in range(1, 6):
            raise ValueError("Choose a rating from 1 to 5.")
        comments = comments.strip()
        if len(comments) > 1000:
            raise ValueError("Feedback comments must be no more than 1000 characters.")
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT * FROM complaints WHERE complaint_id = %s", (complaint_id,))
            row = cursor.fetchone()
            if not row or not student.can_view_complaint(Complaint(row)):
                raise PermissionError("You cannot provide feedback for this complaint.")
            if row["status"] != "Resolved":
                raise ValueError("Feedback is available after a complaint is resolved.")
            cursor.execute(
                """INSERT INTO feedback
                   (complaint_id, student_id, rating, issue_fixed, comments)
                   VALUES (%s, %s, %s, %s, %s)""",
                (complaint_id, student.user_id, rating, issue_fixed, comments or None),
            )

    def add_department(self, admin, name, description):
        if not isinstance(admin, Admin):
            raise PermissionError("Only administrators may add departments.")
        name = name.strip()
        description = description.strip()
        if not name or len(name) > 100 or len(description) > 500:
            raise ValueError("Enter a department name (maximum 100 characters) and description (maximum 500).")
        with database_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO departments (department_name, description) VALUES (%s, %s)",
                (name, description or None),
            )

    def map_category(self, admin, category_id, department_id):
        if not isinstance(admin, Admin):
            raise PermissionError("Only administrators may change category mappings.")
        try:
            category_id = int(category_id)
            department_id = int(department_id) if department_id else None
        except (TypeError, ValueError):
            raise ValueError("Choose valid category and department values.")
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT category_id FROM complaint_categories WHERE category_id = %s", (category_id,))
            if not cursor.fetchone():
                raise ValueError("Choose a valid category.")
            cursor.execute(
                "UPDATE complaint_categories SET default_department_id = %s WHERE category_id = %s",
                (department_id, category_id),
            )

    def add_faculty(self, admin, name, email, password, department_id):
        if not isinstance(admin, Admin):
            raise PermissionError("Only administrators may create faculty accounts.")
        name = name.strip()
        email = email.strip().lower()
        if not name or len(name) > 100 or "@" not in email or len(email) > 255:
            raise ValueError("Enter a valid name and email address.")
        if not faculty_email_matches_institute_domain(email):
            domain = getenv("FACULTY_EMAIL_DOMAIN", "").strip().lower().lstrip("@")
            raise ValueError(f"Faculty email must end with @{domain}.")
        if len(password) < 8:
            raise ValueError("The initial password must contain at least 8 characters.")
        try:
            department_id = int(department_id)
        except (TypeError, ValueError):
            raise ValueError("Choose a valid department.")
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT department_id FROM departments WHERE department_id = %s", (department_id,))
            if not cursor.fetchone():
                raise ValueError("Choose a valid department.")
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise ValueError("An account with that email already exists.")
            cursor.execute(
                """INSERT INTO users (name, email, password_hash, role, department_id)
                   VALUES (%s, %s, %s, 'faculty', %s)""",
                (name, email, generate_password_hash(password), department_id),
            )

    def create_initial_admin(self, name, email, password):
        name = name.strip()
        email = email.strip().lower()
        if not name or "@" not in email or len(password) < 8:
            raise ValueError("Provide a name, valid email, and password of at least 8 characters.")
        with database_cursor(commit=True) as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'")
            if cursor.fetchone()["total"]:
                raise ValueError("An administrator already exists; refusing to create another setup admin.")
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise ValueError("An account with that email already exists.")
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                (name, email, generate_password_hash(password)),
            )
