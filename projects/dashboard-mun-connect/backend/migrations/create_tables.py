"""
Script to create database tables.
"""
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app import create_app, db
from app.core.models import Profile, Document, Speech, Committee, ResearchQuery

def create_tables():
    """Create all database tables."""
    app = create_app("development")
    with app.app_context():
        # Create tables
        db.create_all()
        print("Tables created successfully.")

if __name__ == "__main__":
    create_tables() 