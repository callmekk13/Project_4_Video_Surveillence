import sqlite3 as sl
import os

def init_db(db_path='data.db'):
    con = sl.connect(db_path)
    with con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS USER (
                id TEXT NOT NULL PRIMARY KEY,
                name TEXT,
                location TEXT,
                time TEXT
            );
        """)
    return con

if __name__ == '__main__':
    # When run directly, print all users
    con = init_db('data.db')
    with con:
        data = con.execute("SELECT * FROM USER")
        for row in data:
            print(row)