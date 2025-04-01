from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Just add routine_id column to workout table if it doesn't exist
        db.session.execute(text('ALTER TABLE workout ADD COLUMN routine_id INTEGER'))
        db.session.commit()
        print("Successfully added routine_id column to Workout model")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding column: {str(e)}")
        # Column might already exist
        print("Column may already exist, continuing...") 