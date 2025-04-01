from app import create_app, db
from app.models import User, Exercise, Routine, SharedRoutine
import json
from datetime import datetime

def create_test_shared_routine():
    """Create a test shared routine for demonstration purposes"""
    app = create_app()
    
    with app.app_context():
        print("Creating test shared routine...")
        
        # Get first user
        user = User.query.first()
        if not user:
            print("No users found in the database")
            return
            
        # Get some exercises
        exercises = Exercise.query.limit(4).all()
        if not exercises or len(exercises) < 3:
            print("Not enough exercises found in the database")
            return
            
        # Create exercise data
        exercise_data = []
        for i, exercise in enumerate(exercises):
            exercise_data.append({
                'id': exercise.id,
                'name': exercise.name,
                'input_type': exercise.input_type,
                'sets': [
                    {
                        'weight': 50 if 'weight' in exercise.input_type else None,
                        'reps': 10 if 'reps' in exercise.input_type else None,
                        'time': 60 if 'duration' in exercise.input_type else None,
                        'distance': 1.0 if 'distance' in exercise.input_type else None,
                        'additional_weight': 10 if exercise.input_type == 'weighted_bodyweight' else None,
                        'assistance_weight': 10 if exercise.input_type == 'assisted_bodyweight' else None,
                        'set_type': 'normal'
                    } for _ in range(3)  # 3 sets per exercise
                ]
            })
            
        # Create a routine first (may not be necessary, but helps for testing)
        routine = Routine(
            user_id=user.id,
            name="Test Routine For Explore",
            level="intermediate",
            goal="strength",
            muscle_groups="Chest,Back,Shoulders",
            exercises=json.dumps(exercise_data),
            is_public=True,
            description="A test routine created specifically for the explore feature demonstration."
        )
        db.session.add(routine)
        db.session.flush()  # To get routine.id
        
        # Create a shared routine directly
        shared_routine = SharedRoutine(
            original_id=routine.id,
            name="Shared Test Routine",
            level="intermediate",
            goal="strength",
            muscle_groups="Chest,Back,Shoulders",
            exercises=json.dumps(exercise_data),
            description="This routine is manually created for testing the explore feature.",
            user_id=user.id,
            copy_count=5,
            created_at=datetime.now()
        )
        db.session.add(shared_routine)
        
        # Create a second shared routine for testing
        shared_routine2 = SharedRoutine(
            original_id=routine.id,
            name="Another Shared Routine",
            level="beginner",
            goal="hypertrophy",
            muscle_groups="Legs,Core",
            exercises=json.dumps(exercise_data),
            description="A second test routine for the explore page.",
            user_id=user.id,
            copy_count=2,
            created_at=datetime.now()
        )
        db.session.add(shared_routine2)
        
        db.session.commit()
        
        # Verify
        count = SharedRoutine.query.count()
        print(f"Successfully created test shared routines. Total shared routines: {count}")

if __name__ == "__main__":
    create_test_shared_routine() 