"""
One-time script to fix exercise IDs in the workout data.
This will ensure that exercise IDs are stored as integers in the JSON data.
"""

import json
import os
import sys

# Add the app directory to the path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Workout

app = create_app()

def fix_exercise_ids():
    """Fix exercise IDs in all workout data"""
    print("Starting exercise ID fix script...")
    
    with app.app_context():
        # Get all workouts
        workouts = Workout.query.all()
        print(f"Found {len(workouts)} workouts to process")
        
        fixed_count = 0
        
        for workout in workouts:
            if workout.data:
                try:
                    data = json.loads(workout.data)
                    modified = False
                    
                    if 'exercises' in data:
                        for exercise in data['exercises']:
                            if 'id' in exercise:
                                old_id = exercise['id']
                                # Convert to integer
                                try:
                                    new_id = int(str(old_id))
                                    if new_id != old_id or not isinstance(old_id, int):
                                        exercise['id'] = new_id
                                        modified = True
                                        print(f"Fixed exercise ID: {old_id} -> {new_id} in workout {workout.id}")
                                except (ValueError, TypeError):
                                    print(f"Could not convert exercise ID: {old_id} in workout {workout.id}")
                    
                    # Save changes if data was modified
                    if modified:
                        workout.data = json.dumps(data)
                        fixed_count += 1
                
                except Exception as e:
                    print(f"Error processing workout {workout.id}: {e}")
        
        # Commit all changes
        if fixed_count > 0:
            print(f"Saving {fixed_count} modified workouts...")
            db.session.commit()
            print("Changes saved successfully")
        else:
            print("No workouts needed to be fixed")

if __name__ == "__main__":
    fix_exercise_ids()
    print("Script complete") 