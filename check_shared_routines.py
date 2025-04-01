from app import create_app, db
from app.models import Routine, SharedRoutine, User

def check_shared_routines():
    app = create_app()
    with app.app_context():
        # Get counts
        public_routines = Routine.query.filter_by(is_public=True).all()
        shared_routines = SharedRoutine.query.all()
        
        print(f"=== SHARED ROUTINES STATUS ===")
        print(f"Total routines: {Routine.query.count()}")
        print(f"Public routines: {len(public_routines)}")
        print(f"Shared routines: {len(shared_routines)}")
        print()
        
        # Check each public routine
        print(f"=== PUBLIC ROUTINES ===")
        missing_shared = []
        for routine in public_routines:
            # Get user info
            user = User.query.get(routine.user_id)
            username = user.username if user else "Unknown"
            
            # Check if there's a shared version
            shared = SharedRoutine.query.filter_by(original_id=routine.id).first()
            
            print(f"ID: {routine.id}, Name: {routine.name}, User: {username}, Is Public: {routine.is_public}")
            if shared:
                print(f"  → Has shared version with ID: {shared.id}")
            else:
                print(f"  → Missing shared version!")
                missing_shared.append(routine)
        
        print()
        
        # Check each shared routine
        print(f"=== SHARED ROUTINES ===")
        for shared in shared_routines:
            # Get user info
            user = User.query.get(shared.user_id)
            username = user.username if user else "Unknown"
            
            # Check original routine
            original = Routine.query.get(shared.original_id) if shared.original_id else None
            
            print(f"ID: {shared.id}, Name: {shared.name}, User: {username}, Original ID: {shared.original_id}")
            if original:
                print(f"  → Original routine exists, Is Public: {original.is_public}")
            else:
                print(f"  → Original routine not found!")
        
        # Fix missing shared routines if needed
        if missing_shared:
            print("\n=== FIXING MISSING SHARED ROUTINES ===")
            fixed_count = 0
            for routine in missing_shared:
                print(f"Creating shared routine for public routine ID: {routine.id}, Name: {routine.name}")
                
                # Create a shared version
                shared_routine = SharedRoutine(
                    original_id=routine.id,
                    name=routine.name,
                    level=routine.level,
                    goal=routine.goal,
                    muscle_groups=routine.muscle_groups,
                    description=routine.description,
                    exercises=routine.exercises,
                    user_id=routine.user_id,
                    created_at=routine.created_at if hasattr(routine, 'created_at') else None,
                    copy_count=0
                )
                db.session.add(shared_routine)
                fixed_count += 1
            
            db.session.commit()
            print(f"Fixed {fixed_count} routines by creating shared versions")
        else:
            print("No fixes needed")

if __name__ == "__main__":
    check_shared_routines() 