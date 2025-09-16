import mysql.connector
from mysql.connector import Error

class Config:
    # Flask secret key
    SECRET_KEY = 'SCD123!'  # You can change this to any random string

    # Database configuration (match scd.sql)
    DB_HOST = 'localhost'
    DB_USER = 'appuser'                  # 👈 use the user created in scd.sql
    DB_PASSWORD = 'StrongPasswordHere!'  # 👈 same as in scd.sql
    DB_NAME = 'employee_db'              # 👈 database created in scd.sql

    @staticmethod
    def get_db_connection():
        """
        Returns a MySQL database connection.
        Returns None if connection fails.
        """
        try:
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
            return None
