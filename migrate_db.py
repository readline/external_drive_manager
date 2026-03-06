#!/usr/bin/env python3
"""Database migration script to add new columns"""

import sqlite3
from pathlib import Path

def migrate_database():
    db_path = Path("data/catalog.db")
    
    if not db_path.exists():
        print("Database does not exist. It will be created automatically on next startup.")
        return
    
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns in drives table
    cursor.execute("PRAGMA table_info(drives)")
    columns = {col[1] for col in cursor.fetchall()}
    
    # Add note column if missing
    if "note" not in columns:
        print("Adding 'note' column to drives table...")
        cursor.execute("ALTER TABLE drives ADD COLUMN note TEXT")
    else:
        print("'note' column already exists.")
    
    # Add total_capacity column if missing
    if "total_capacity" not in columns:
        print("Adding 'total_capacity' column to drives table...")
        cursor.execute("ALTER TABLE drives ADD COLUMN total_capacity INTEGER")
    else:
        print("'total_capacity' column already exists.")
    
    # Add available_space column if missing
    if "available_space" not in columns:
        print("Adding 'available_space' column to drives table...")
        cursor.execute("ALTER TABLE drives ADD COLUMN available_space INTEGER")
    else:
        print("'available_space' column already exists.")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
