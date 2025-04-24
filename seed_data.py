import sys
import os
import json
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Session, Exercise, Routine, Measurement, Statistic, SavedItem, Notification, BodyweightLog, SharedRoutine

def create_sample_exercises():
    """Create a list of common exercises"""
    exercises = [
        {
            'name': 'Bench Press',
            'equipment': 'Barbell',
            'muscles_worked': 'Chest, Triceps, Shoulders',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'bench_press.jpg'
        },
        {
            'name': 'Squat',
            'equipment': 'Barbell',
            'muscles_worked': 'Quadriceps, Hamstrings, Glutes',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'squat.jpg'
        },
        {
            'name': 'Deadlift',
            'equipment': 'Barbell',
            'muscles_worked': 'Lower Back, Hamstrings, Glutes',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'deadlift.jpg'
        },
        {
            'name': 'Pull-ups',
            'equipment': 'Pull-up Bar',
            'muscles_worked': 'Lats, Biceps',
            'exercise_type': 'strength',
            'input_type': 'bodyweight_reps',
            'photo': 'pullups.jpg'
        },
        {
            'name': 'Running',
            'equipment': 'None',
            'muscles_worked': 'Full Body',
            'exercise_type': 'cardio',
            'input_type': 'distance_duration',
            'photo': 'running.jpg'
        },
        {
            'name': 'Dumbbell Rows',
            'equipment': 'Dumbbells',
            'muscles_worked': 'Upper Back, Biceps',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'dumbbell_rows.jpg'
        },
        {
            'name': 'Push-ups',
            'equipment': 'None',
            'muscles_worked': 'Chest, Triceps, Shoulders',
            'exercise_type': 'strength',
            'input_type': 'bodyweight_reps',
            'photo': 'pushups.jpg'
        },
        {
            'name': 'Shoulder Press',
            'equipment': 'Dumbbells',
            'muscles_worked': 'Shoulders, Triceps',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'shoulder_press.jpg'
        },
        {
            'name': 'Leg Press',
            'equipment': 'Machine',
            'muscles_worked': 'Quadriceps, Hamstrings, Glutes',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'leg_press.jpg'
        },
        {
            'name': 'Bicep Curls',
            'equipment': 'Dumbbells',
            'muscles_worked': 'Biceps',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'bicep_curls.jpg'
        },
        {
            'name': 'Lat Pulldown',
            'equipment': 'Cable Machine',
            'muscles_worked': 'Lats, Biceps',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'lat_pulldown.jpg'
        },
        {
            'name': 'Hip Abduction',
            'equipment': 'Machine',
            'muscles_worked': 'Abductors',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'hip_abduction.jpg'
        },
        {
            'name': 'Hip Adduction',
            'equipment': 'Machine',
            'muscles_worked': 'Adductors',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'hip_adduction.jpg'
        },
        {
            'name': 'Back Extension',
            'equipment': 'Machine',
            'muscles_worked': 'Lower Back',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'back_extension.jpg'
        },
        {
            'name': 'Bent Over Rows',
            'equipment': 'Barbell',
            'muscles_worked': 'Upper Back, Lats',
            'exercise_type': 'strength',
            'input_type': 'weight_reps',
            'photo': 'bent_over_rows.jpg'
        },
        {
            'name': 'Weighted Pull-ups',
            'equipment': 'Pull-up Bar, Weight Belt',
            'muscles_worked': 'Lats, Biceps',
            'exercise_type': 'strength',
            'input_type': 'weighted_bodyweight',
            'photo': 'weighted_pullups.jpg'
        },
        {
            'name': 'Assisted Pull-ups',
            'equipment': 'Assisted Pull-up Machine',
            'muscles_worked': 'Lats, Biceps',
            'exercise_type': 'strength',
            'input_type': 'assisted_bodyweight',
            'photo': 'assisted_pullups.jpg'
        },
        {
            'name': 'Plank',
            'equipment': 'None',
            'muscles_worked': 'Abdominals',
            'exercise_type': 'strength',
            'input_type': 'duration',
            'photo': 'plank.jpg'
        },
        {
            'name': 'Weighted Plank',
            'equipment': 'Weight Plate',
            'muscles_worked': 'Abdominals',
            'exercise_type': 'strength',
            'input_type': 'duration_weight',
            'photo': 'weighted_plank.jpg'
        },
        {
            'name': 'Farmers Walk',
            'equipment': 'Dumbbells',
            'muscles_worked': 'Forearms, Traps, Shoulders',
            'exercise_type': 'strength',
            'input_type': 'weight_distance',
            'photo': 'farmers_walk.jpg'
        }
    ]

    created_exercises = []
    for exercise_data in exercises:
        exercise = Exercise(
            name=exercise_data['name'],
            equipment=exercise_data['equipment'],
            muscles_worked=exercise_data['muscles_worked'],
            exercise_type=exercise_data['exercise_type'],
            input_type=exercise_data['input_type'],
            photo=exercise_data['photo'],
            user_created=False
        )
        db.session.add(exercise)
        created_exercises.append(exercise)

    return created_exercises

def create_sample_users():
    """Create 10 sample users with varied data"""
    first_names = ['John', 'Emma', 'Michael', 'Sarah', 'David', 'Lisa', 'James', 'Anna', 'Robert', 'Maria']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']

    users = []
    for i in range(10):
        exp = random.randint(100, 3000)
        level = exp // 100
        if level == 0:
            level = 1

        # Generate random bodyweight (in kg)
        bodyweight = round(random.uniform(50, 100), 1)  # Random weight between 50kg and 100kg

        # Create user with unit preferences
        user = User(
            first_name=first_names[i],
            last_name=last_names[i],
            username=f'user{i+1}',
            email=f'user{i+1}@example.com',
            level=level,
            exp=exp,
            streak=random.randint(0, 60),
            preferred_weight_unit=random.choice(['kg', 'lbs']),
            preferred_distance_unit=random.choice(['km', 'mi']),
            preferred_measurement_unit=random.choice(['cm', 'in']),
            privacy_setting=random.choice(['public', 'private'])
        )
        user.set_password(f'password{i+1}')
        db.session.add(user)
        db.session.flush()  # Ensure user.id is available

        # Create initial bodyweight log (always stored in kg)
        initial_weight = Measurement(
            user_id=user.id,
            type='weight',
            value=bodyweight,  # Already in kg
            unit='kg',
            date=datetime.utcnow()
        )
        db.session.add(initial_weight)

        users.append(user)

    db.session.commit()  # Commit users and bodyweight logs

    # Create some follow relationships
    for user in users:
        # Calculate maximum number of users that can be followed (excluding self)
        max_follows = min(7, len(users) - 1)  # Can't follow more users than exist (minus self)
        min_follows = min(3, max_follows)  # Ensure minimum doesn't exceed maximum

        # Each user follows a random number of users between min_follows and max_follows
        num_to_follow = random.randint(min_follows, max_follows)
        available_users = [u for u in users if u != user]
        to_follow = random.sample(available_users, num_to_follow)

        for followed_user in to_follow:
            user.following.append(followed_user)

    return users

def create_sample_routines(users, exercises):
    """Create sample routines for users"""
    routine_names = ['Push Day', 'Pull Day', 'Leg Day', 'Full Body', 'Upper Body']
    levels = ['beginner', 'intermediate', 'advanced']
    goals = ['strength', 'hypertrophy', 'endurance']
    
    routines = []

    for user in users:
        num_routines = random.randint(1, 3)
        for _ in range(num_routines):
            routine_exercises = random.sample(exercises, random.randint(3, 6))
            exercise_data = []
            for exercise in routine_exercises:
                exercise_data.append({
                    'id': exercise.id,
                    'name': exercise.name,
                    'input_type': exercise.input_type,
                    'sets': [
                        {
                            'weight': random.randint(20, 100) if 'weight' in exercise.input_type else None,
                            'reps': random.randint(8, 12) if 'reps' in exercise.input_type else None,
                            'time': random.randint(30, 180) if 'duration' in exercise.input_type else None,
                            'distance': round(random.uniform(1, 5), 2) if 'distance' in exercise.input_type else None,
                            'additional_weight': random.randint(5, 25) if exercise.input_type == 'weighted_bodyweight' else None,
                            'assistance_weight': random.randint(5, 25) if exercise.input_type == 'assisted_bodyweight' else None,
                            'set_type': 'normal'
                        } for _ in range(random.randint(3, 5))
                    ]
                })

            # Create routine
            is_public = random.random() < 0.4  # 40% chance of being public
            routine = Routine(
                user_id=user.id,
                name=random.choice(routine_names),
                level=random.choice(levels),
                goal=random.choice(goals),
                muscle_groups=','.join(random.sample(['Chest', 'Back', 'Shoulders', 'Arms', 'Legs', 'Core'], random.randint(1, 3))),
                exercises=json.dumps(exercise_data),
                is_public=is_public,
                description=f"A sample {random.choice(['beginner', 'intermediate', 'advanced'])} {random.choice(['strength', 'hypertrophy', 'endurance'])} routine."
            )
            db.session.add(routine)
            routines.append(routine)
    
    # Commit routines first so they have IDs
    db.session.commit()
    
    # Create shared versions of public routines
    for routine in routines:
        if routine.is_public:
            shared_routine = SharedRoutine(
                original_id=routine.id,
                name=routine.name,
                level=routine.level,
                goal=routine.goal,
                muscle_groups=routine.muscle_groups,
                exercises=routine.exercises,
                description=routine.description,
                user_id=routine.user_id,
                copy_count=random.randint(0, 10)
            )
            db.session.add(shared_routine)

def create_sample_sessions(users, exercises):
    """Create workout sessions for users"""
    for user in users:
        # Create sessions over the last 30 days
        for days_ago in range(30):
            if random.random() < 0.7:  # 70% chance of having a workout each day
                session_exercises = random.sample(exercises, random.randint(3, 6))
                exercise_data = []
                for exercise in session_exercises:
                    if exercise.input_type == 'weight_reps':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'reps': random.randint(8, 12),
                            'weight': random.randint(20, 100)
                        })
                    elif exercise.input_type == 'bodyweight_reps':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'reps': random.randint(8, 12)
                        })
                    elif exercise.input_type == 'weighted_bodyweight':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'reps': random.randint(8, 12),
                            'additional_weight': random.randint(5, 20)
                        })
                    elif exercise.input_type == 'assisted_bodyweight':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'reps': random.randint(8, 12),
                            'assistance_weight': random.randint(5, 20)
                        })
                    elif exercise.input_type == 'duration':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'time': random.randint(30, 600)  # Duration in seconds
                        })
                    elif exercise.input_type == 'distance_duration':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'distance': round(random.uniform(1, 10), 2),  # Distance in km
                            'time': random.randint(300, 1800)  # Duration in seconds
                        })
                    elif exercise.input_type == 'weight_distance':
                        exercise_data.append({
                            'exercise_id': exercise.id,
                            'sets': random.randint(3, 5),
                            'weight': random.randint(20, 100),
                            'distance': round(random.uniform(1, 10), 2)  # Distance in km
                        })

                session = Session(
                    user_id=user.id,
                    session_date=datetime.utcnow() - timedelta(days=days_ago),
                    duration=f'{random.randint(30, 90)} minutes',
                    volume=random.randint(1000, 5000),
                    exercises=json.dumps(exercise_data),
                    exp_gained=random.randint(100, 500),
                    session_rating=random.randint(1, 5),
                    description=f'Workout {30-days_ago}'
                )
                db.session.add(session)

def create_sample_measurements(users):
    """Create measurement history for users"""
    measurement_types = ['Weight', 'Body Fat %', 'Chest', 'Waist', 'Arms']

    for user in users:
        for measurement_type in measurement_types:
            base_value = random.uniform(60, 90) if measurement_type == 'Weight' else random.uniform(10, 30)
            for days_ago in range(30):
                if random.random() < 0.3:  # 30% chance of taking measurement each day
                    value = base_value + random.uniform(-2, 2)
                    measurement = Measurement(
                        user_id=user.id,
                        type=measurement_type,
                        value=round(value, 1),
                        date=datetime.utcnow() - timedelta(days=days_ago)
                    )
                    db.session.add(measurement)

def seed_database():
    """Main function to seed the database with sample data"""
    app = create_app()

    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Creating exercises...")
        exercises = create_sample_exercises()
        db.session.commit()

        print("Creating users...")
        users = create_sample_users()
        db.session.commit()

        print("Creating routines...")
        create_sample_routines(users, exercises)
        db.session.commit()

        print("Creating sessions...")
        create_sample_sessions(users, exercises)
        db.session.commit()

        print("Creating measurements...")
        create_sample_measurements(users)
        db.session.commit()

        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()