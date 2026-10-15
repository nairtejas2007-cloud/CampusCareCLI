# CampusCare CLI

A command-line interface for the CampusCare complaint system. This repository contains no Flask pages. It uses Python functions for the menus and reuses the same service/model logic for MySQL validation, department routing, permissions, status history, and feedback.

## Requirements

- Python 3.11
- MySQL 8.0 with the `campuscare` schema

## Setup on Windows

Open PowerShell in this repository folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally with the MySQL username, password, and database name. Never commit `.env`.

If your MySQL server does not already have the CampusCare tables, review `schema.sql` and apply it to the intended database. It uses `IF NOT EXISTS` and contains no drop/delete statements.

Create the first administrator only if your database does not already have one:

```powershell
python create_admin.py
```

Run the CLI:

```powershell
python .\campuscare_cli\main.py
```

## Menus

- Students can register, submit complaints, list their own complaints, view status history, and submit feedback after resolution.
- Faculty can view complaints routed to their department, inspect details/history/student feedback, and update status.
- Administrators can view all complaints, update statuses, assign departments, manage category routing, create department accounts, and export a CSV report.

The CLI shares the `users`, `departments`, `complaint_categories`, `complaints`, `complaint_updates`, and `feedback` tables with the website. It does not create separate account or complaint data.

## Files

- `campuscare_cli/main.py`: input prompts and role-based menus.
- `services.py`: shared validation and database operations.
- `models.py`: small user and complaint classes used for permissions and status rules.
- `database.py`: reads local MySQL settings from `.env`.
- `reporting.py`: builds the administrator CSV export.
- `create_admin.py`: secure first-admin setup with hidden password prompts.
- `schema.sql`: the shared relational schema and seed departments/categories.
