import os
import getpass
import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

username = input("Account username [ali]: ").strip() or "ali"
password = getpass.getpass("Enter the new password: ")
confirm = getpass.getpass("Confirm the new password: ")

if not password or password != confirm:
    raise SystemExit("Passwords are empty or do not match.")

conn = pymysql.connect(
    host="localhost",
    user=os.environ.get("DB_USER", "ali"),
    password=os.environ["DB_PASSWORD"],
    database="restaurant",
    charset="utf8mb4",
)

try:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE staff
            SET password_hash = %s
            WHERE username = %s AND is_active = 1
            """,
            (generate_password_hash(password), username),
        )

        if cur.rowcount != 1:
            conn.rollback()
            raise SystemExit(
                f"Expected one account to update; got {cur.rowcount}. "
                "Check the username and active account."
            )

    conn.commit()
    print("Password hash updated successfully.")
finally:
    conn.close()

