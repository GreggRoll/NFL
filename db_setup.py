import sqlite3
from datetime import datetime

def create_live_chat_database():
    conn = sqlite3.connect('data-log.db')  # This will create the database file
    cursor = conn.cursor()

    # Create a table for chat messages
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY,
        ip TEXT NOT NULL,
        username TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

def create_data_log_database():
    conn = sqlite3.connect('data-log.db')  # This will create the database file
    cursor = conn.cursor()

    # Create a table for NFL data
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS nfl_data (
        datetime TEXT,
        game_id TEXT,
        date TEXT,
        home_team TEXT,
        away_team TEXT,
        home_win INTEGER,
        away_win INTEGER,
        points REAL
    )
    ''')

    conn.commit()
    conn.close()

def insert_sample_chat(data):
    conn = sqlite3.connect('data-log.db')
    cursor = conn.cursor()

    for entry in data:
        cursor.execute("INSERT INTO chat_messages (id, ip, username, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (entry['id'], entry['ip'], entry['username'], entry['message'], entry['timestamp']))

    conn.commit()
    conn.close()

# Sample data
sample_data = [
    {"id": 1, "ip": "127.0.51.1", "username": "Lion-Red", "message": "This site is Awesome!", "timestamp": "2023-12-06T11:07:58.977884"},
    {"id": 2, "ip": "127.0.0.1", "username": "Admin-Gold", "message": "Thank you!", "timestamp": "2023-12-06T14:52:31.223164"}
]

create_live_chat_database()
create_data_log_database()
insert_sample_chat(sample_data)