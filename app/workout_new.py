def calculate_workout_metrics(workout_data):
    """
    Calculate workout metrics from the workout data.
    Returns a dictionary with volume, duration, and rating.
    """
    # Initialize metrics
    total_volume = 0
    max_exercise_duration = 0
    timer_duration = workout_data.get('duration', 0)
    rating = workout_data.get('rating', 3)
    
    # Extract exercises data
    exercises = workout_data.get('exercises', [])
    
    # Calculate total volume and find max exercise duration
    for exercise in exercises:
        if isinstance(exercise, dict):
            # Add exercise volume if directly available
            if 'volume' in exercise and exercise['volume']:
                try:
                    total_volume += float(exercise['volume'])
                except (ValueError, TypeError):
                    pass
                
            # Handle exercise duration
            if 'duration' in exercise and exercise['duration']:
                try:
                    duration = float(exercise['duration'])
                    max_exercise_duration = max(max_exercise_duration, duration)
                except (ValueError, TypeError):
                    pass
                    
            # Process sets if available
            if 'sets' in exercise and isinstance(exercise['sets'], list):
                for set_data in exercise['sets']:
                    if isinstance(set_data, dict):
                        # Add set volume if available
                        if 'volume' in set_data and set_data['volume']:
                            try:
                                total_volume += float(set_data['volume'])
                            except (ValueError, TypeError):
                                pass
                                
                        # Calculate volume from weight and reps if available
                        elif 'weight' in set_data and 'reps' in set_data:
                            try:
                                weight = float(set_data['weight'])
                                reps = float(set_data['reps'])
                                total_volume += weight * reps
                            except (ValueError, TypeError):
                                pass
                                
                        # Check for set duration/time
                        if 'time' in set_data and set_data['time']:
                            try:
                                time = float(set_data['time'])
                                max_exercise_duration = max(max_exercise_duration, time)
                            except (ValueError, TypeError):
                                pass
    
    # Use the longer of timer duration or max exercise duration
    final_duration = max(timer_duration, max_exercise_duration)
    
    return {
        'volume': round(total_volume, 1),
        'duration': int(final_duration),
        'rating': rating
    } 
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from flask_login import login_required, current_user
from .models import Exercise, Session, User, Measurement, Set, Routine, Workout, WorkoutExercise, WorkoutSet, SharedRoutine, WorkoutLike, WorkoutComment, Notification
from . import db
import json
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
import random

workout = Blueprint('workout', __name__)

@workout.route('/start-workout')
@login_required
def start_workout():
    # Check if user wants to repeat a workout
    repeat_id = request.args.get('repeat')
    prefilled_exercises = []
    
    # Get all exercises for display
    exercises = Exercise.query.order_by(Exercise.name).all()
    
    # Get the 5 most recent completed exercises
    recent_exercise_data = db.session.query(
        Set.exercise_id, 
        func.max(Session.session_date).label('last_date')
    ).join(Session).filter(
        Session.user_id == current_user.id,
        Set.completed == True
    ).group_by(Set.exercise_id).order_by(
        desc('last_date')
    ).limit(8).all()
    
    # Get objects for the recent exercises
    recent_exercises_ids = [data[0] for data in recent_exercise_data]
    recent_exercises = Exercise.query.filter(Exercise.id.in_(recent_exercises_ids)).all()
    
    # If a workout is being repeated, get its exercises
    if repeat_id:
        try:
            # Get the session
            session = Session.query.filter_by(id=repeat_id, user_id=current_user.id).first()
            
            if session:
                # See if there's a structured workout object
                workout = Workout.query.filter_by(
                    user_id=current_user.id,
                    date=session.session_date
                ).first()
                
                if workout and workout.data:
                    # Parse the workout data
                    workout_data = json.loads(workout.data)
                    if 'exercises' in workout_data:
                        for ex in workout_data['exercises']:
                            if 'id' in ex and 'sets' in ex:
                                # Add to prefilled exercises
                                exercise = Exercise.query.get(ex['id'])
                                if not exercise:
                                    continue
                                    
                                exercise_data = {
                                    'id': exercise.id,
                                    'name': exercise.name,
                                    'input_type': exercise.input_type,
                                    'sets': []
                                }
                                
                                # Add the sets
                                for s in ex['sets']:
                                    set_data = {
                                        'weight': s.get('weight'),
                                        'reps': s.get('reps'),
                                        'time': s.get('time'),
                                        'distance': s.get('distance'),
                                        'additional_weight': s.get('additional_weight'),
                                        'assistance_weight': s.get('assistance_weight')
                                    }
                                    exercise_data['sets'].append(set_data)
                                
                                prefilled_exercises.append(exercise_data)
                else:
                    # Get the exercises and sets from the old format
                    completed_sets = Set.query.filter_by(
                        session_id=repeat_id, 
                        completed=True
                    ).order_by(Set.exercise_id, Set.order).all()
                    
                    current_exercise = None
                    current_exercise_data = None
                    
                    for s in completed_sets:
                        # If this is a new exercise, create a new entry
                        if not current_exercise or current_exercise.id != s.exercise_id:
                            if current_exercise_data:
                                prefilled_exercises.append(current_exercise_data)
                            
                            current_exercise = Exercise.query.get(s.exercise_id)
                            if not current_exercise:
                                continue
                                
                            current_exercise_data = {
                                'id': s.exercise_id,
                                'name': current_exercise.name,
                                'input_type': current_exercise.input_type,
                                'sets': []
                            }
                        
                        # Add the set data
                        set_data = {
                            'weight': s.weight,
                            'reps': s.reps,
                            'time': s.time,
                            'distance': s.distance,
                            'additional_weight': s.additional_weight,
                            'assistance_weight': s.assistance_weight
                        }
                        current_exercise_data['sets'].append(set_data)
                    
                    # Add the last exercise
                    if current_exercise_data:
                        prefilled_exercises.append(current_exercise_data)
                
                # Save to session for use in the workout
                if prefilled_exercises:
                    request.session['repeat_workout_exercises'] = prefilled_exercises
                    
        except Exception as e:
            print(f"Error repeating workout: {str(e)}")
            return redirect(url_for('workout.start_workout'))
    
    # Sort all exercises: recent first, then alphabetically
    def sort_key(exercise):
        try:
            # Calculate a score based on recency
            if exercise.id in recent_exercises_ids:
                # Get the index (most recent = 0, oldest = n)
                recency_index = recent_exercises_ids.index(exercise.id)
                # Lower index = higher score
                recency_score = 1000 - recency_index * 100
                return (recency_score, exercise.name)
            else:
                # Not recently used, lowest priority but still sorted by name
                return (0, exercise.name)
        except:
            # Fallback if there's any error
            return (0, exercise.name)
    
    sorted_exercises = sorted(exercises, key=sort_key, reverse=True)
    
    # Add a recency index to the exercise dictionary for additional sorting in JS
    for i, ex in enumerate(recent_exercises):
        ex.recent_index = i
    
    # Get the user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    user_weight = latest_bodyweight.value if latest_bodyweight else None
    
    # Get current user's unread notification count
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).count()
    
    # Check if there are prefilled exercises from previous attempt
    if request.session.get('repeat_workout_exercises'):
        prefilled_exercises = request.session.get('repeat_workout_exercises')
        request.session.pop('repeat_workout_exercises', None)
    
    return render_template('workout/start.html',
                          exercises=sorted_exercises,
                          recent_exercises=recent_exercises,
                          prefilled_exercises=prefilled_exercises,
                          user_weight=user_weight,
                          unread_count=unread_count)

@workout.route('/log-workout', methods=['POST'])
@login_required
def log_workout():
    data = request.get_json()
    exercises_data = data.get('exercises', [])

    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    bodyweight = latest_bodyweight.value if latest_bodyweight else None

    try:
        # Create new session
        new_session = Session(
            user_id=current_user.id,
            session_date=datetime.utcnow(),
            duration=f"{data.get('duration', 0)} seconds",
            title=data.get('title', 'Workout'),
            description=data.get('description', ''),
            session_rating=data.get('rating', 5),
            photo=data.get('photo_url', None),
            volume=data.get('volume', 0)  # Store volume from client
        )
        
        # Try to set the new columns, but handle if they don't exist
        try:
            new_session.sets_completed = data.get('sets_completed', 0)
            new_session.total_reps = data.get('total_reps', 0)
        except Exception as column_error:
            print(f"Warning: Could not set new columns: {str(column_error)}")
            # Continue without these fields
        
        db.session.add(new_session)
        db.session.flush()  # Get new_session.id

        total_volume = 0
        formatted_exercises = []

        # Process each exercise and its sets
        for exercise_data in exercises_data:
            exercise = Exercise.query.get(exercise_data['id'])
            if not exercise:
                continue

            completed_sets = [set for set in exercise_data['sets'] if set.get('completed', False)]
            if not completed_sets:
                continue

            formatted_exercises.append({
                'name': exercise.name,
                'sets': len(completed_sets)
            })

            # Create Set records and calculate volume
            for set_idx, set_data in enumerate(completed_sets):
                set_volume = exercise.calculate_volume(set_data, bodyweight)
                total_volume += set_volume

                # Create new Set record with all fields
                new_set = Set(
                    exercise_id=exercise.id,
                    session_id=new_session.id,
                    completed=True,
                    order=set_idx,
                    set_type=set_data.get('set_type', 'normal'),
                    volume=set_volume  # Store the calculated volume
                )

                # Add all relevant fields based on exercise type
                for field in exercise.get_input_fields():
                    setattr(new_set, field, set_data.get(field, 0))

                    # Check if set is within range and set the flag
                    if exercise and exercise.range_enabled:
                        within_range = False
                        
                        if exercise.input_type.endswith('reps'):
                            if exercise.min_reps and exercise.max_reps:
                                reps = set_data.get('reps', 0)
                                within_range = exercise.min_reps <= reps <= exercise.max_reps
                        elif exercise.input_type.endswith('duration'):
                            if exercise.min_duration and exercise.max_duration:
                                time = set_data.get('time', 0)
                                within_range = exercise.min_duration <= time <= exercise.max_duration
                        elif exercise.input_type.endswith('distance'):
                            if exercise.min_distance and exercise.max_distance:
                                distance = set_data.get('distance', 0)
                                within_range = exercise.min_distance <= distance <= exercise.max_distance
                        
                        new_set.within_range = within_range

                db.session.add(new_set)

        # Update session with total volume and exercise data
        new_session.exercises = json.dumps(formatted_exercises)
        
        # If client provided volume is 0, use our calculated volume
        if new_session.volume == 0:
            new_session.volume = total_volume
        
        # Format duration properly for display
        duration_seconds = data.get('duration', 0)
        if duration_seconds:
            try:
                # Ensure duration_seconds is an integer before division
                if isinstance(duration_seconds, str):
                    duration_seconds = int(duration_seconds.strip())
                minutes = int(duration_seconds) // 60  # Use integer division
                new_session.duration = f"{minutes} minutes"
            except (ValueError, TypeError) as e:
                print(f"Error formatting duration: {str(e)}")
                new_session.duration = "0 minutes"  # Default if conversion fails
        
        # Use the EXP gained during the workout from the client
        base_exp = data.get('exp_gained', 0)
        
        # Calculate consistency bonus
        consistency_bonus = 0
        
        # Check workout frequency (last 7 days)
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_workouts = Session.query.filter(
            Session.user_id == current_user.id,
            Session.session_date >= one_week_ago
        ).count()
        
        # Bonus for multiple workouts per week
        if recent_workouts >= 3:
            consistency_bonus += 20  # Bonus for 3+ workouts per week
        elif recent_workouts >= 1:
            consistency_bonus += 10  # Smaller bonus for at least 1 workout per week
        
        # Check for streaks (consecutive days)
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        
        worked_out_yesterday = Session.query.filter(
            Session.user_id == current_user.id,
            Session.session_date >= yesterday_start,
            Session.session_date <= yesterday_end
        ).first() is not None
        
        # Update streak
        if worked_out_yesterday:
            # If they worked out yesterday, increment streak
            current_user.streak += 1
        else:
            # Reset streak if they didn't work out yesterday
            current_user.streak = 1
        
        # Bonus for maintaining streak
        if current_user.streak >= 7:
            consistency_bonus += 30  # Bonus for 7+ day streak
        elif current_user.streak >= 3:
            consistency_bonus += 15  # Bonus for 3+ day streak
        
        # Set total EXP gained (base + bonus)
        total_exp_gained = base_exp + consistency_bonus
        new_session.exp_gained = total_exp_gained

        # Update user's exp
        current_user.exp += total_exp_gained
        current_user.update_level()

        db.session.commit()
        return jsonify({
            'success': True,
            'session_id': new_session.id,
            'exp_gained': total_exp_gained
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error saving workout: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 
