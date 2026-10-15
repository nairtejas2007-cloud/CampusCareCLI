
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)


def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "campuscare"),
        connection_timeout=5,
    )
