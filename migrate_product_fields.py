#!/usr/bin/env python3
"""
Database migration script to add product fields to the Job table.
Run this script to update your existing database with the new product information fields.
"""

from sqlalchemy import text
from src.database import engine, SessionLocal
from src.config import DB_TYPE

def migrate_database():
    """Add product fields to the jobs table."""
    print("Starting database migration to add product fields...")
    
    with engine.connect() as connection:
        try:
            # Add the new columns to the jobs table
            if DB_TYPE == 'sqlite':
                # SQLite syntax
                connection.execute(text("ALTER TABLE jobs ADD COLUMN product_name VARCHAR"))
                connection.execute(text("ALTER TABLE jobs ADD COLUMN product_url VARCHAR"))
                connection.execute(text("ALTER TABLE jobs ADD COLUMN affiliate_commission VARCHAR"))
            elif DB_TYPE == 'postgresql':
                # PostgreSQL syntax
                connection.execute(text("ALTER TABLE jobs ADD COLUMN product_name VARCHAR"))
                connection.execute(text("ALTER TABLE jobs ADD COLUMN product_url VARCHAR"))
                connection.execute(text("ALTER TABLE jobs ADD COLUMN affiliate_commission VARCHAR"))
            
            connection.commit()
            print("✅ Successfully added product fields to jobs table:")
            print("   - product_name")
            print("   - product_url")
            print("   - affiliate_commission")
            
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️  Product fields already exist in the database. No migration needed.")
            else:
                print(f"❌ Error during migration: {e}")
                raise

def main():
    """Run the migration."""
    migrate_database()
    print("\n🎉 Migration completed successfully!")
    print("\nYour database now supports storing:")
    print("- Product names")
    print("- Product URLs") 
    print("- Affiliate commission rates")
    print("\nThese will be automatically saved with each video when you run the pipeline.")

if __name__ == "__main__":
    main() 