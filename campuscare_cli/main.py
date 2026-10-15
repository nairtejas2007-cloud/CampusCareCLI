"""Terminal version of CampusCare using the existing services and database."""

from datetime import datetime
from getpass import getpass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mysql.connector

from models import Admin, Complaint, Faculty, Student
from reporting import complaints_to_csv
from services import ComplaintManagementSystem, database_cursor

system = ComplaintManagementSystem()


def read_text(prompt, allow_blank=False):
    while True:
        value = input(prompt).strip()
        if value or allow_blank:
            return value
        print("Please enter a value.")


def read_number(prompt, minimum, maximum):
    while True:
        value = input(prompt).strip()
        if value.isdigit() and minimum <= int(value) <= maximum:
            return int(value)
        print(f"Enter a number from {minimum} to {maximum}.")


def choose_from_list(title, rows, label_key):
    if not rows:
        print("No options are available.")
        return None
    print(f"\n{title}")
    for number, row in enumerate(rows, 1):
        print(f"  {number}. {row[label_key]}")
    choice = read_number("Choose a number (0 to cancel): ", 0, len(rows))
    return rows[choice - 1] if choice else None


def print_table(headers, rows):
    if not rows:
        print("No records found.")
        return
    text_rows = [["-" if value is None else str(value) for value in row] for row in rows]
    widths = [
        max(len(str(header)), *(len(row[column]) for row in text_rows))
        for column, header in enumerate(headers)
    ]
    line = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    print(line)
    print("| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(headers)) + " |")
    print(line)
    for row in text_rows:
        print("| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |")
    print(line)


def format_time(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value or "-")


def print_complaints(user):
    complaints = system.get_complaints(user)
    rows = [
        (
            complaint["complaint_id"],
            complaint["title"],
            complaint["category_name"],
            complaint["priority"],
            complaint["status"],
            complaint["department_name"] or "Awaiting assignment",
            format_time(complaint["created_at"]),
        )
        for complaint in complaints
    ]
    print_table(("ID", "Title", "Category", "Priority", "Status", "Department", "Submitted"), rows)


def choose_complaint(user):
    complaints = system.get_complaints(user)
    if not complaints:
        print("No complaints are available to your account.")
        return None
    print_table(
        ("ID", "Title", "Category", "Status"),
        [
            (row["complaint_id"], row["title"], row["category_name"], row["status"])
            for row in complaints
        ],
    )
    valid_ids = {row["complaint_id"] for row in complaints}
    while True:
        value = input("Complaint ID (blank to cancel): ").strip()
        if not value:
            return None
        if value.isdigit() and int(value) in valid_ids:
            return int(value)
        print("Choose a complaint ID from the list above.")


def show_complaint_details(user):
    complaint_id = choose_complaint(user)
    if complaint_id is None:
        return
    details = system.get_complaint_details(user, complaint_id)
    if not details:
        print("That complaint is not available to this account.")
        return

    print(f"\nCOMPLAINT #{details['complaint_id']}: {details['title']}")
    print(f"Category: {details['category_name']}")
    print(f"Status: {details['status']} | Priority: {details['priority']}")
    print(f"Department: {details['department_name'] or 'Awaiting assignment'}")
    print(f"Submitted by: {details['student_name']}")
    print(f"Location: {details['location'] or 'Not provided'}")
    print(f"Submitted: {format_time(details['created_at'])}")
    print(f"Last updated: {format_time(details['updated_at'])}")
    print("Description:")
    print(details["description"])

    print("\nSTATUS HISTORY")
    for update in details["history"]:
        previous = f" (from {update['old_status']})" if update["old_status"] else " (submission)"
        print(f"  {format_time(update['updated_at'])}: {update['new_status']}{previous}")
        print(f"    By: {update['updated_by_name']}")
        print(f"    Remark: {update['remarks'] or 'No remark provided.'}")

    feedback = details["feedback"]
    if feedback:
        print("\nSTUDENT FEEDBACK")
        print(f"Rating: {feedback['rating']} / 5")
        print(f"Issue fixed: {'Yes' if feedback['issue_fixed'] else 'No'}")
        print(f"Comment: {feedback['comments'] or 'No comment provided.'}")
        print(f"Submitted: {format_time(feedback['created_at'])}")
    elif details["status"] == "Resolved" and isinstance(user, Student):
        print("\nThis complaint is resolved. You may leave one feedback entry.")
        if input("Submit feedback now? (y/n): ").strip().lower() in {"y", "yes"}:
            rating = read_number("Rating (1-5): ", 1, 5)
            issue_fixed = input("Was the issue fixed? (y/n): ").strip().lower()
            while issue_fixed not in {"y", "yes", "n", "no"}:
                issue_fixed = input("Enter y or n: ").strip().lower()
            comments = read_text("Comment (optional): ", allow_blank=True)
            system.submit_feedback(user, complaint_id, rating, issue_fixed in {"y", "yes"}, comments)
            print("Feedback submitted.")


def submit_complaint(student):
    categories = system.get_categories()
    category = choose_from_list("COMPLAINT CATEGORIES", categories, "category_name")
    if category is None:
        return
    title = read_text("Title: ")
    print("Description (maximum 500 words):")
    description = read_text("> ")
    location = read_text("Location (optional): ", allow_blank=True)
    priorities = ({"priority": name} for name in ("Low", "Normal", "High"))
    priority = choose_from_list("PRIORITY", list(priorities), "priority")
    if priority is None:
        return
    complaint_id = system.create_complaint(
        student,
        {
            "category_id": str(category["category_id"]),
            "title": title,
            "description": description,
            "location": location,
            "priority": priority["priority"],
        },
    )
    print(f"Complaint #{complaint_id} submitted.")


def update_status(user):
    complaint_id = choose_complaint(user)
    if complaint_id is None:
        return
    details = system.get_complaint_details(user, complaint_id)
    if not details:
        print("That complaint is not available to this account.")
        return
    print("\nCurrent status:", details["status"])
    for number, status in enumerate(Complaint.STATUS_CHOICES, 1):
        print(f"  {number}. {status}")
    new_status = Complaint.STATUS_CHOICES[
        read_number("Choose a status: ", 1, len(Complaint.STATUS_CHOICES)) - 1
    ]
    remarks = read_text("Remark (required for Resolved or Rejected): ", allow_blank=True)
    system.update_complaint_status(user, complaint_id, new_status, remarks)
    print("Status updated and recorded in the complaint history.")


def assign_department(admin):
    complaint_id = choose_complaint(admin)
    if complaint_id is None:
        return
    departments = system.get_departments()
    department = choose_from_list("ASSIGN DEPARTMENT (or choose 0 to leave unassigned)", departments, "department_name")
    department_id = department["department_id"] if department else None
    system.assign_complaint(admin, complaint_id, department_id)
    print("Department assignment saved.")


def map_category(admin):
    categories = system.get_categories()
    departments = system.get_departments()
    category = choose_from_list("CATEGORIES", categories, "category_name")
    if category is None:
        return
    department = choose_from_list("DEFAULT DEPARTMENT (or choose 0 for manual assignment)", departments, "department_name")
    department_id = department["department_id"] if department else None
    system.map_category(admin, category["category_id"], department_id)
    print("Category routing saved.")


def add_department(admin):
    name = read_text("Department name: ")
    description = read_text("Description (optional): ", allow_blank=True)
    system.add_department(admin, name, description)
    print("Department added.")


def add_faculty_account(admin):
    name = read_text("Faculty/staff name: ")
    email = read_text("Institute email: ").lower()
    password = getpass("Initial password (hidden): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match. No account was created.")
        return
    departments = system.get_departments()
    department = choose_from_list("DEPARTMENT", departments, "department_name")
    if department is None:
        return
    system.add_faculty(admin, name, email, password, department["department_id"])
    print("Faculty/staff account created. Share the initial password securely.")


def show_admin_report(admin):
    complaints = system.get_complaints(admin)
    counts = {status: 0 for status in Complaint.STATUS_CHOICES}
    for complaint in complaints:
        counts[complaint["status"]] += 1
    print("\nCOMPLAINT COUNTS BY STATUS")
    print_table(("Status", "Count"), counts.items())
    if input("Export all complaints to CSV? (y/n): ").strip().lower() in {"y", "yes"}:
        report_folder = PROJECT_ROOT / "reports"
        report_folder.mkdir(exist_ok=True)
        report_path = report_folder / "campuscare-cli-report.csv"
        report_path.write_text(complaints_to_csv(complaints), encoding="utf-8-sig")
        print("Report saved to:", report_path)


def run_action(action, user):
    try:
        action(user)
    except (ValueError, PermissionError) as error:
        print("Could not complete that action:", error)
    except mysql.connector.Error:
        print("A database error occurred. Check MySQL and your local .env settings.")


def student_menu(user):
    while True:
        print(f"\nSTUDENT MENU — {user.name}")
        print("1. View my complaints")
        print("2. Submit a complaint")
        print("3. View complaint details, history, or feedback")
        print("4. Log out")
        choice = read_number("Choose: ", 1, 4)
        if choice == 1:
            run_action(print_complaints, user)
        elif choice == 2:
            run_action(submit_complaint, user)
        elif choice == 3:
            run_action(show_complaint_details, user)
        else:
            break


def faculty_menu(user):
    while True:
        print(f"\nDEPARTMENT MENU — {user.name} (department ID {user.department_id})")
        print("1. View department complaints")
        print("2. View details, history, and student feedback")
        print("3. Update a complaint status")
        print("4. Log out")
        choice = read_number("Choose: ", 1, 4)
        if choice == 1:
            run_action(print_complaints, user)
        elif choice == 2:
            run_action(show_complaint_details, user)
        elif choice == 3:
            run_action(update_status, user)
        else:
            break


def admin_menu(user):
    actions = {
        1: ("View all complaints", print_complaints),
        2: ("View details, history, and feedback", show_complaint_details),
        3: ("Update a complaint status", update_status),
        4: ("Assign a complaint to a department", assign_department),
        5: ("Update a category's default department", map_category),
        6: ("Add a department", add_department),
        7: ("Create a faculty/staff account", add_faculty_account),
        8: ("Reports and CSV export", show_admin_report),
    }
    while True:
        print(f"\nADMIN MENU — {user.name}")
        for number, (label, _) in actions.items():
            print(f"{number}. {label}")
        print("9. Log out")
        choice = read_number("Choose: ", 1, 9)
        if choice == 9:
            break
        run_action(actions[choice][1], user)


def register_student(_user=None):
    name = read_text("Name: ")
    email = read_text("Email: ").lower()
    password = getpass("Password (hidden): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match. No account was created.")
        return
    system.register_student(name, email, password)
    print("Student account created. You can now log in.")


def login(_user=None):
    email = read_text("Email: ").lower()
    password = getpass("Password (hidden): ")
    user = system.authenticate_user(email, password)
    if user is None:
        print("Email or password is incorrect.")
        return
    print(f"\nWelcome, {user.name}.")
    if isinstance(user, Student):
        student_menu(user)
    elif isinstance(user, Faculty):
        faculty_menu(user)
    elif isinstance(user, Admin):
        admin_menu(user)


def main():
    while True:
        print("\nCAMPUSCARE — COMMAND LINE")
        print("1. Log in")
        print("2. Register as a student")
        print("3. Exit")
        choice = read_number("Choose: ", 1, 3)
        if choice == 1:
            run_action(login, None)
        elif choice == 2:
            run_action(register_student, None)
        else:
            print("Goodbye.")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCampusCare CLI closed.")
