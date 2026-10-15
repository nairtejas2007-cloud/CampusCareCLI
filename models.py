class User:
    """Common account data and the default complaint permission."""

    def __init__(self, user_id, name, email, role, department_id=None):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role
        self.department_id = department_id

    def can_view_complaint(self, complaint):
        return False


class Student(User):
    def __init__(self, user_id, name, email, role="student", department_id=None):
        super().__init__(user_id, name, email, role, department_id)

    def can_view_complaint(self, complaint):
        return complaint.student_id == self.user_id


class Faculty(User):
    def __init__(self, user_id, name, email, role="faculty", department_id=None):
        super().__init__(user_id, name, email, role, department_id)

    def can_view_complaint(self, complaint):
        return complaint.assigned_department_id == self.department_id


class Admin(User):
    def __init__(self, user_id, name, email, role="admin", department_id=None):
        super().__init__(user_id, name, email, role, department_id)

    def can_view_complaint(self, complaint):
        return True


class Complaint:
    STATUS_CHOICES = (
        "Submitted",
        "Under Review",
        "In Progress",
        "Resolved",
        "Rejected",
    )
    STATUS_TRANSITIONS = {
        "Submitted": {"Submitted", "Under Review", "In Progress", "Resolved", "Rejected"},
        "Under Review": {"Submitted", "Under Review", "In Progress", "Resolved", "Rejected"},
        "In Progress": {"Submitted", "Under Review", "In Progress", "Resolved", "Rejected"},
        "Resolved": set(),
        "Rejected": set(),
    }

    def __init__(self, row):
        self.complaint_id = row["complaint_id"]
        self.student_id = row["student_id"]
        self.title = row["title"]
        self.category_id = row["category_id"]
        self.description = row["description"]
        self.status = row["status"]
        self.assigned_department_id = row["assigned_department_id"]
        self.assigned_staff_id = row["assigned_staff_id"]

    def update_status(self, new_status, remarks=""):
        if new_status not in self.STATUS_CHOICES:
            raise ValueError("Choose a valid complaint status.")
        if new_status not in self.STATUS_TRANSITIONS[self.status]:
            raise ValueError("That status change is not allowed.")
        if new_status == "Rejected" and not remarks.strip():
            raise ValueError("A rejection reason is required.")
        if new_status == "Resolved" and not remarks.strip():
            raise ValueError("Add a resolution remark before resolving the complaint.")
        old_status = self.status
        self.status = new_status
        return old_status

    def assign_department(self, department_id):
        self.assigned_department_id = department_id
