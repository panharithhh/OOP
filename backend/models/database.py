
import mysql.connector
# This relative import is correct for the file's location in models/
from config.settings import settings


def get_db_connection():
    """
    Creates and returns a new database connection instance.

    IMPORTANT: The part of your code that calls this function is now
    responsible for closing the connection when it's done.
    Failure to close connections will lead to resource leaks.
    
    Example:
        db = get_db_connection()
        # ... do work ...
        db.close()
    """
    db_connection = None
    try:
        # Establish the connection using your settings
        db_connection = mysql.connector.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        # Return the connection object
        return db_connection
    except mysql.connector.Error as err:
        # If the connection fails, print an error and return None
        print(f"Error connecting to database: {err}")
        return None

