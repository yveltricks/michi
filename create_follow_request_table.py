"""
Script to create the FollowRequest table in the database.
Run this script with: python create_follow_request_table.py
"""
from app import app, db
from app.models import FollowRequest
import os

with app.app_context():
    # Check if the table exists
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'follow_request' not in tables:
        print("Creating follow_request table...")
        # Create just the follow_request table
        FollowRequest.__table__.create(db.engine)
        print("follow_request table created successfully")
    else:
        print("follow_request table already exists")
    
    # Print all existing tables
    print("\nExisting tables:")
    for table in sorted(tables):
        print(f"- {table}") 