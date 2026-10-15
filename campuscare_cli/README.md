# CampusCare CLI

This is a command-line version of CampusCare. It is separate from the Flask website and uses the same MySQL database, accounts, and complaint records. It does not create or alter tables.

## Run it

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\campuscare_cli\main.py
```

To create the first administrator, run the existing secure setup script once:

```powershell
.\.venv\Scripts\python.exe .\create_admin.py
```

The setup script uses hidden password entry and refuses to create another setup admin if one already exists. Then choose **Log in** in the CLI.

## Menus

- Students can register, submit complaints, list only their own complaints, view history, and provide feedback after resolution.
- Faculty can list complaints routed to their department, view details/history/student feedback, and update status.
- Administrators can view all complaints, update or reassign departments, manage category routing, create department accounts, and export a CSV report.

Passwords use the same hash verification as the website. All role and department checks, validation, department mapping, status history, and feedback rules are delegated to the existing `services.py` and `models.py` code. The command-line screens themselves use ordinary functions; they do not introduce another application class or duplicate the business logic.

The CLI writes administrator CSV exports to `reports/campuscare-cli-report.csv`. The existing `.gitignore` excludes the `reports/` directory.
