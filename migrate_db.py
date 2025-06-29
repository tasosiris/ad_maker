import sqlite3
import os
from pathlib import Path
from src.config import DB_PATH

def migrate_database():
    """Add missing content column to scripts table"""
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} does not exist.")
        return False
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the content column exists
        cursor.execute("PRAGMA table_info(scripts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "content" not in columns:
            print("Adding missing 'content' column to scripts table...")
            cursor.execute("ALTER TABLE scripts ADD COLUMN content TEXT;")
            conn.commit()
            print("Successfully added 'content' column to scripts table!")
        else:
            print("Content column already exists in scripts table.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error migrating database: {e}")
        return False

if __name__ == "__main__":
    if migrate_database():
        print("Database migration completed successfully.")
    else:
        print("Database migration failed.") 