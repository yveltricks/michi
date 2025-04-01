from app import create_app, db
from app.models import User, Routine, SharedRoutine
import json

def check_routines():
    """Check public and shared routines status"""
    app = create_app()
    with app.app_context():
        print("\n=== CHECKING ROUTINES STATUS ===")
        
        # Get all routines
        all_routines = Routine.query.all()
        public_routines = Routine.query.filter_by(is_public=True).all()
        shared_routines = SharedRoutine.query.all()
        
        print(f"Total routines: {len(all_routines)}")
        print(f"Public routines: {len(public_routines)}")
        print(f"Shared routines: {len(shared_routines)}")
        
        # List public routines
        print("\n=== PUBLIC ROUTINES ===")
        for routine in public_routines:
            user = User.query.get(routine.user_id)
            username = user.username if user else "Unknown"
            print(f"ID: {routine.id}, Name: {routine.name}, User: {username}, Is Public: {routine.is_public}")
            
            # Check if this public routine has a shared counterpart
            shared = SharedRoutine.query.filter_by(original_id=routine.id).first()
            if shared:
                print(f"  → Has shared version with ID: {shared.id}")
            else:
                print("  ✗ No shared version found!")
        
        # List shared routines
        print("\n=== SHARED ROUTINES ===")
        for shared in shared_routines:
            user = User.query.get(shared.user_id)
            username = user.username if user else "Unknown"
            original = Routine.query.get(shared.original_id) if shared.original_id else None
            
            print(f"ID: {shared.id}, Name: {shared.name}, User: {username}, Original ID: {shared.original_id}")
            if original:
                print(f"  → Original routine exists, Is Public: {original.is_public}")
            else:
                print("  ✗ Original routine not found!")
        
        # Let's create shared routines for public routines that don't have one
        print("\n=== FIXING MISSING SHARED ROUTINES ===")
        fixed_count = 0
        
        for routine in public_routines:
            shared = SharedRoutine.query.filter_by(original_id=routine.id).first()
            if not shared:
                print(f"Creating shared routine for public routine ID: {routine.id}, Name: {routine.name}")
                
                # Create a shared version
                new_shared = SharedRoutine(
                    original_id=routine.id,
                    name=routine.name,
                    level=routine.level,
                    goal=routine.goal,
                    muscle_groups=routine.muscle_groups,
                    description=routine.description,
                    exercises=routine.exercises,
                    user_id=routine.user_id,
                    created_at=routine.created_at,
                    copy_count=0
                )
                
                db.session.add(new_shared)
                fixed_count += 1
        
        # Commit changes if any fixes were made
        if fixed_count > 0:
            db.session.commit()
            print(f"Fixed {fixed_count} routines by creating shared versions")
        else:
            print("No fixes needed")

if __name__ == "__main__":
    check_routines() 