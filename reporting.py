import csv
from datetime import date
from io import StringIO


def count_report_items(report):
    """Recursively total integer counts in a nested report dictionary."""
    if isinstance(report, dict):
        return sum(count_report_items(value) for value in report.values())
    return int(report)


def prepare_complaint_report(rows, *statuses, **filters):
    """Filter complaint rows and sort newest first for tables or CSV export."""
    selected_statuses = {status for status in statuses if status}
    category = filters.get("category")
    department = filters.get("department")
    status_filter = filters.get("status")
    start_value = filters.get("from_date")
    end_value = filters.get("to_date")
    try:
        start_date = date.fromisoformat(start_value) if start_value else None
        end_date = date.fromisoformat(end_value) if end_value else None
    except ValueError as error:
        raise ValueError("Choose valid start and end dates.") from error
    if start_date and end_date and start_date > end_date:
        raise ValueError("The start date must not be after the end date.")

    filtered_rows = []
    for row in rows:
        if selected_statuses and row["status"] not in selected_statuses:
            continue
        if status_filter and row["status"] != status_filter:
            continue
        if category and row["category_name"] != category:
            continue
        if department and row.get("department_name") != department:
            continue
        created_date = row["created_at"].date()
        if start_date and created_date < start_date:
            continue
        if end_date and created_date > end_date:
            continue
        filtered_rows.append(row)
    return sorted(filtered_rows, key=lambda row: row["created_at"], reverse=True)


def complaints_to_csv(rows):
    """Create a simple CSV report in memory for a browser download."""
    columns = (
        "complaint_id",
        "title",
        "category_name",
        "student_name",
        "department_name",
        "status",
        "priority",
        "created_at",
    )
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if column == "created_at" and value:
                value = value.strftime("%Y-%m-%d %H:%M")
            values.append(value if value is not None else "")
        writer.writerow(values)
    return output.getvalue()
