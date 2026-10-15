from getpass import getpass

import mysql.connector

from services import ComplaintManagementSystem


def main():
    print("Create the first CampusCare administrator")
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip()
    password = getpass("Password (at least 8 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("The passwords do not match.")
        return
    try:
        ComplaintManagementSystem().create_initial_admin(name, email, password)
        print("Administrator account created. You can now log in to the website.")
    except ValueError as error:
        print(error)
    except mysql.connector.Error:
        print("The administrator could not be created. Check the MySQL connection and schema.")


if __name__ == "__main__":
    main()
