from app import create_app, db
from app.models import Session

# Initialize the Flask app
app = create_app()

# Run the cleanup within the app context
with app.app_context():
    # Find all sessions with invalid duration values
    sessions = Session.query.filter(Session.duration.is_(None)).all()
    
    # Update each session's duration to "0 minutes"
    for session in sessions:
        session.duration = "0 minutes"
    
    # Commit the changes to the database
    db.session.commit()
    
    print(f"Updated {len(sessions)} sessions with invalid duration values.")