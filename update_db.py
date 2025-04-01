from app import create_app, db
from app.models import SharedRoutine
from sqlalchemy import inspect

def update_database():
    """
    Update the database schema to include the SharedRoutine model.
    """
    app = create_app()
    
    with app.app_context():
        # Check if SharedRoutine table already exists
        inspector = inspect(db.engine)
        if 'shared_routine' not in inspector.get_table_names():
            print("Creating SharedRoutine table...")
            
            # Create just the SharedRoutine table
            db.metadata.tables['shared_routine'].create(db.engine)
            print("SharedRoutine table created successfully.")
        else:
            print("SharedRoutine table already exists.")

if __name__ == "__main__":
    update_database() 