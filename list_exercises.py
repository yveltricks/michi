from app import create_app, db
from app.models import Exercise

app = create_app()

with app.app_context():
    exercises = Exercise.query.all()
    for exercise in exercises:
        print(f"{exercise.id}: {exercise.name}") 