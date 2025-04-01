from app import create_app, db
from app.models import User, Routine, SharedRoutine
import json
from datetime import datetime

def seed_shared_routines():
    """Seed sample shared routines for testing the explore feature"""
    app = create_app()
    with app.app_context():
        print("Creating sample shared routines...")
        
        # Get the first user from the database
        user = User.query.first()
        if not user:
            print("No users found. Please run seed_data.py first.")
            return
            
        # Sample routine 1: Full Body Beginner
        sample_routine1 = SharedRoutine(
            original_id=1,  # This would typically be an actual routine ID
            name="Full Body Beginner Workout",
            level="Beginner",
            goal="Strength",
            muscle_groups="Full Body",
            description="A perfect beginner routine targeting all major muscle groups",
            exercises=json.dumps([
                {
                    "id": 1,
                    "sets": [
                        {"weight": 20, "reps": 10},
                        {"weight": 25, "reps": 8},
                        {"weight": 30, "reps": 6}
                    ]
                },
                {
                    "id": 2,
                    "sets": [
                        {"weight": 15, "reps": 12},
                        {"weight": 15, "reps": 12},
                        {"weight": 15, "reps": 12}
                    ]
                }
            ]),
            user_id=user.id,
            created_at=datetime.now(),
            copy_count=5
        )
        
        # Sample routine 2: Upper Body Intermediate
        sample_routine2 = SharedRoutine(
            original_id=2,
            name="Upper Body Power Workout",
            level="Intermediate",
            goal="Hypertrophy",
            muscle_groups="Arms,Chest,Back",
            description="Focus on building upper body strength and muscle mass",
            exercises=json.dumps([
                {
                    "id": 3,
                    "sets": [
                        {"weight": 40, "reps": 8},
                        {"weight": 45, "reps": 6},
                        {"weight": 50, "reps": 4}
                    ]
                },
                {
                    "id": 4,
                    "sets": [
                        {"weight": 30, "reps": 10},
                        {"weight": 35, "reps": 8},
                        {"weight": 40, "reps": 6}
                    ]
                }
            ]),
            user_id=user.id,
            created_at=datetime.now(),
            copy_count=3
        )
        
        # Sample routine 3: Leg Day Advanced
        sample_routine3 = SharedRoutine(
            original_id=3,
            name="Advanced Leg Day Crusher",
            level="Advanced",
            goal="Strength",
            muscle_groups="Legs",
            description="High intensity leg workout for experienced athletes",
            exercises=json.dumps([
                {
                    "id": 5,
                    "sets": [
                        {"weight": 100, "reps": 6},
                        {"weight": 110, "reps": 4},
                        {"weight": 120, "reps": 2}
                    ]
                },
                {
                    "id": 6,
                    "sets": [
                        {"weight": 80, "reps": 8},
                        {"weight": 90, "reps": 6},
                        {"weight": 100, "reps": 4}
                    ]
                }
            ]),
            user_id=user.id,
            created_at=datetime.now(),
            copy_count=7
        )
        
        # Add the routines to the database
        db.session.add(sample_routine1)
        db.session.add(sample_routine2)
        db.session.add(sample_routine3)
        
        # Commit the changes
        db.session.commit()
        
        print("Sample shared routines created successfully!")

if __name__ == "__main__":
    seed_shared_routines() 