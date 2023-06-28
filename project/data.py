import sqlite3

def get_db_connection():
    conn = sqlite3.connect("project.db")
    return conn

def close_db_connection(conn):
    conn.close()

def execute_query(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if params:
        cursor.execute(query, params)
    
    else:
        cursor.execute(query)
    
    result = cursor.fetchall()

    cursor.close()
    close_db_connection(conn)
    return result
"""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL
);
"""