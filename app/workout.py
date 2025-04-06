from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Exercise, Session, User, Measurement, Set, Routine, Workout, WorkoutExercise, WorkoutSet, SharedRoutine
from . import db
import json
from datetime import datetime, timedelta, time
from sqlalchemy import or_, func

# Constants for workout options
WORKOUT_LEVELS = ['Beginner', 'Intermediate', 'Advanced']
WORKOUT_GOALS = ['Strength', 'Hypertrophy', 'Endurance', 'Weight Loss', 'General Fitness']
MUSCLE_GROUPS = ['Chest', 'Back', 'Shoulders', 'Arms', 'Core', 'Legs', 'Full Body']

workout = Blueprint('workout', __name__)

@workout.route('/start-workout')
@login_required
def start_workout():
    """
    This route shows the workout creation page where users can
    select exercises and start logging their workout.
    """
    # Get all available exercises
    all_exercises = Exercise.query.all()
    
    # Find recently used exercise IDs from completed workouts
    recent_exercise_ids = []
    
    # Get the user's recent workouts
    recent_workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date.desc()).limit(10).all()
    
    for workout in recent_workouts:
        if workout.data:
            try:
                data = json.loads(workout.data)
                if 'exercises' in data:
                    for ex in data['exercises']:
                        # Add the exercise ID to our list if not already present
                        ex_id = ex.get('id')
                        if ex_id and ex_id not in recent_exercise_ids:
                            recent_exercise_ids.append(int(ex_id))
            except Exception as e:
                print(f"Error parsing workout data: {e}")
    
    print(f"Recent exercise IDs: {recent_exercise_ids}")
    
    # Sort exercises - recently used first, then alphabetically
    def sort_key(exercise):
        try:
            # Get the index in recent exercises (lower is more recent)
            recent_index = recent_exercise_ids.index(exercise.id) if exercise.id in recent_exercise_ids else float('inf')
            return (recent_index, exercise.name)
        except Exception as e:
            print(f"Error sorting exercise {exercise.id}: {e}")
            return (float('inf'), exercise.name)
    
    sorted_exercises = sorted(all_exercises, key=sort_key)
    
    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    user_weight = latest_bodyweight.value if latest_bodyweight else None
    
    return render_template('workout/start.html', exercises=sorted_exercises, user_weight=user_weight)

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
            minutes = int(duration_seconds / 60)
            new_session.duration = f"{minutes} minutes"
        
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

@workout.route('/api/previous-values/<int:exercise_id>')
@login_required
def get_previous_values(exercise_id):
    # Get the last completed session that has this exercise with completed sets
    subquery = db.session.query(Session.id)\
        .join(Set)\
        .filter(
            Session.user_id == current_user.id,
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Session.session_date.desc())\
        .limit(1)\
        .subquery()

    previous_sets = Set.query\
        .filter(
            Set.session_id.in_(subquery),
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Set.order)\
        .all()

    # Add some debug logging
    print(f"Found {len(previous_sets)} previous sets for exercise {exercise_id}")
    for set in previous_sets:
        print(f"Set {set.order + 1}: {set.weight}kg x {set.reps} reps")

    return jsonify([{
        'weight': set.weight,
        'reps': set.reps,
        'order': set.order
    } for set in previous_sets])

@workout.route('/api/previous-values/<int:exercise_id>/<int:set_number>')
@login_required
def get_specific_previous_value(exercise_id, set_number):
    # Get the last completed session that has this exercise with completed sets
    subquery = db.session.query(Session.id)\
        .join(Set)\
        .filter(
            Session.user_id == current_user.id,
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Session.session_date.desc())\
        .limit(1)\
        .subquery()

    previous_set = Set.query\
        .filter(
            Set.session_id.in_(subquery),
            Set.exercise_id == exercise_id,
            Set.order == set_number - 1,  # Convert to 0-based index
            Set.completed == True
        )\
        .first()

    if not previous_set:
        print(f"No previous set found for exercise {exercise_id}, set number {set_number}")
        return jsonify(None)

    print(f"Found previous set: {previous_set.weight}kg x {previous_set.reps} reps")
    return jsonify({
        'weight': previous_set.weight,
        'reps': previous_set.reps
    })

@workout.route('/workout/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View a specific workout session"""
    # Import unit conversion function
    from .utils import convert_volume_to_preferred_unit
    
    if session_id is None or session_id == 'null':
        flash('Invalid session ID.', 'danger')
        return redirect(url_for('workout.workout_page'))
    
    # Try to find the workout
    workout = Workout.query.get(session_id)
    
    # If workout not found, check if it's a routine workout
    if not workout:
        print(f"Workout with ID {session_id} not found, checking for recent workouts")
        # Look for most recent workouts
        recent_workouts = Workout.query.filter_by(user_id=current_user.id)\
            .order_by(Workout.date.desc())\
            .limit(1)\
            .all()
        
        if recent_workouts:
            workout = recent_workouts[0]
            print(f"Using most recent workout with ID {workout.id} instead")
        else:
            flash('Workout session not found.', 'danger')
            return redirect(url_for('workout.workout_page'))
    
    # Check if user can view this session
    if workout.user_id != current_user.id:
        flash('You do not have permission to view this session.', 'danger')
        return redirect(url_for('workout.workout_page'))
    
    # Get exercises for the session
    exercises = []
    workout_data = {}
    
    # Parse workout data if available
    if workout.data:
        try:
            workout_data = json.loads(workout.data)
        except Exception as e:
            print(f"Error parsing workout data: {e}")
            workout_data = {}
    
    # First try to get exercises from the relationship
    if workout.exercises:
        try:
            for we in workout.exercises:
                exercise = Exercise.query.get(we.exercise_id)
                if exercise:
                    # Count completed sets
                    completed_sets = [s for s in we.sets if s.completed]
                    
                    # Only add the exercise if it has completed sets
                    if completed_sets:
                        exercise_data = {
                            'id': exercise.id,  # Add the exercise ID
                            'name': exercise.name,
                            'sets': len(completed_sets)
                        }
                        
                        # Add type-specific details
                        if exercise.input_type == 'weight_reps':
                            # Calculate average weight and reps
                            total_weight = sum(s.weight for s in completed_sets if s.weight)
                            total_reps = sum(s.reps for s in completed_sets if s.reps)
                            if total_reps > 0:
                                exercise_data['weight'] = round(total_weight / len(completed_sets), 1)
                                # Convert weight to preferred unit
                                exercise_data['weight'] = convert_volume_to_preferred_unit(
                                    exercise_data['weight'], current_user.preferred_weight_unit)
                                exercise_data['reps'] = round(total_reps / len(completed_sets))
                        
                        elif exercise.input_type == 'duration':
                            # Calculate total duration
                            total_duration = sum(s.duration for s in completed_sets if s.duration)
                            if total_duration > 0:
                                exercise_data['duration'] = round(total_duration / 60, 1)  # Convert to minutes
                        
                        exercises.append(exercise_data)
        except Exception as e:
            print(f"Error parsing workout exercises from relationship: {e}")
    
    # If no exercises found from relationship, try data field
    if not exercises and workout_data:
        try:
            exercises_data = workout_data.get('exercises', [])
            
            for exercise_data in exercises_data:
                if exercise_data.get('sets'):
                    completed_sets = [s for s in exercise_data.get('sets', []) if s.get('completed')]
                    
                    if completed_sets:
                        exercise = {
                            'id': exercise_data.get('id'),  # Add the exercise ID
                            'name': exercise_data.get('name', 'Unknown Exercise'),
                            'sets': len(completed_sets)
                        }
                        
                        # Add type-specific fields
                        if exercise_data.get('input_type') == 'weight_reps':
                            weights = [s.get('weight', 0) for s in completed_sets if s.get('weight')]
                            reps = [s.get('reps', 0) for s in completed_sets if s.get('reps')]
                            
                            if weights and reps:
                                exercise['weight'] = round(sum(weights) / len(weights), 1)
                                # Convert weight to preferred unit
                                exercise['weight'] = convert_volume_to_preferred_unit(
                                    exercise['weight'], current_user.preferred_weight_unit)
                                exercise['reps'] = round(sum(reps) / len(reps))
                        
                        exercises.append(exercise)
        except Exception as e:
            print(f"Error parsing workout exercises from data: {e}")
    
    # Calculate accurate metrics using our helper function
    metrics = calculate_workout_metrics(workout_data)
    
    # Update the workout object with calculated metrics
    if not workout.volume or workout.volume < metrics['volume']:
        workout.volume = metrics['volume']
        
    if not workout.duration or workout.duration < metrics['duration']:
        workout.duration = metrics['duration']
        
    if not workout.rating:
        workout.rating = metrics['rating']
    
    # Save the updated metrics back to the database
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating workout metrics: {e}")
    
    # Convert workout volume to preferred unit for display
    workout.volume = convert_volume_to_preferred_unit(workout.volume, current_user.preferred_weight_unit)
    
    print(f"Returning workout with {len(exercises)} exercises")
    return render_template('workout/view_session.html', 
                          session=workout, 
                          exercises=exercises)

@workout.route('/api/exercises')
@login_required
def get_exercises():
    # Get all exercises 
    exercises = Exercise.query.all()
    
    # Find recently used exercise IDs from completed workouts
    recent_exercise_ids = []
    
    # Get the user's recent workouts
    recent_workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date.desc()).limit(10).all()
    
    for workout in recent_workouts:
        if workout.data:
            try:
                data = json.loads(workout.data)
                if 'exercises' in data:
                    for ex in data['exercises']:
                        # Add the exercise ID to our list if not already present
                        ex_id = ex.get('id')
                        if ex_id and ex_id not in recent_exercise_ids:
                            recent_exercise_ids.append(ex_id)
            except Exception as e:
                print(f"Error parsing workout data: {e}")
    
    # Convert exercises to dict for easier sorting
    exercise_data = [{
        'id': e.id,
        'name': e.name,
        'muscles_worked': e.muscles_worked,
        # Set a sort order based on recent usage
        'recent_index': recent_exercise_ids.index(e.id) if e.id in recent_exercise_ids else float('inf')
    } for e in exercises]
    
    # Sort by recent usage (recently used first), then by name
    exercise_data.sort(key=lambda x: (x['recent_index'], x['name']))
    
    # Remove the sorting field before returning
    for ex in exercise_data:
        ex.pop('recent_index', None)
    
    return jsonify(exercise_data)

@workout.route('/api/exercise-details/<int:exercise_id>')
@login_required
def get_exercise_details(exercise_id):
    try:
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Get the exercise's primary attributes
        exercise_data = {
            'id': exercise.id,
            'name': exercise.name,
            'equipment': exercise.equipment,
            'muscles_worked': exercise.muscles_worked,
            'input_type': exercise.input_type,
            'range_enabled': exercise.range_enabled,
            'rest_duration': exercise.rest_duration
        }
        
        # Get unit preferences for display
        weight_unit = current_user.preferred_weight_unit
        distance_unit = current_user.preferred_distance_unit
        
        # Import conversion utilities
        from .utils import convert_weight, convert_distance
        
        # Add range information based on exercise type
        if exercise.input_type.endswith('reps'):
            exercise_data['min_reps'] = exercise.min_reps
            exercise_data['max_reps'] = exercise.max_reps
        elif exercise.input_type.endswith('duration'):
            exercise_data['min_duration'] = exercise.min_duration
            exercise_data['max_duration'] = exercise.max_duration
        elif exercise.input_type.endswith('distance'):
            # Convert min/max distance if user prefers miles
            if distance_unit == 'mi' and exercise.min_distance is not None:
                exercise_data['min_distance'] = convert_distance(exercise.min_distance, 'km', 'mi')
            else:
                exercise_data['min_distance'] = exercise.min_distance
                
            if distance_unit == 'mi' and exercise.max_distance is not None:
                exercise_data['max_distance'] = convert_distance(exercise.max_distance, 'km', 'mi')
            else:
                exercise_data['max_distance'] = exercise.max_distance
        
        # Get the field units with user preferences
        exercise_data['units'] = exercise.get_units(current_user)
        
        # Get previous sets
        previous_sets = []
        recent_sets = Set.query.filter_by(exercise_id=exercise_id, completed=True).order_by(Set.id.desc()).limit(5).all()
        
        for set_obj in recent_sets:
            # Use to_dict with user preferences
            set_data = set_obj.to_dict(user=current_user)
            previous_sets.append(set_data)
            
        exercise_data['previous_sets'] = previous_sets
        
        # Get exercise history
        history_data = []
        history_sets = Set.query.filter_by(exercise_id=exercise_id, completed=True).order_by(Set.id.desc()).limit(100).all()
        
        # Process history data grouped by session
        sessions = {}
        for set_obj in history_sets:
            session_id = set_obj.session_id
            if session_id not in sessions:
                session = Session.query.get(session_id)
                sessions[session_id] = {
                    'date': session.session_date.strftime('%Y-%m-%d'),
                    'sets': []
                }
            
            # Add set data with unit conversion based on user preferences
            sessions[session_id]['sets'].append(set_obj.to_dict(user=current_user))
        
        # Convert to list and sort by date
        for session_id, session_data in sessions.items():
            history_data.append(session_data)
        
        history_data.sort(key=lambda x: x['date'], reverse=True)
        exercise_data['history'] = history_data
        
        return jsonify(exercise_data)
    except Exception as e:
        print(f"Error getting exercise details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@workout.route('/measurements')
@login_required
def measurements():
    """Render the measurements landing page."""
    # Pass the Measurement class to the template context
    return render_template('workout/measurements.html', Measurement=Measurement)

@workout.route('/measurements/<measurement_type>', methods=['GET'])
@login_required
def track_measurement(measurement_type):
    """Handle displaying measurement tracking pages."""
    valid_types = {
        'weight': {'unit': 'kg', 'min': 5, 'max': 600},
        'body_fat': {'unit': '%', 'min': 1, 'max': 50},
        'chest': {'unit': 'cm', 'min': 50, 'max': 200},
        'waist': {'unit': 'cm', 'min': 40, 'max': 200},
        'hips': {'unit': 'cm', 'min': 50, 'max': 200},
        'neck': {'unit': 'cm', 'min': 20, 'max': 100},
        'left_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'right_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'left_calf': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_calf': {'unit': 'cm', 'min': 10, 'max': 100}
    }
    
    if measurement_type not in valid_types:
        flash('Invalid measurement type')
        return redirect(url_for('workout.measurements'))
    
    # Get measurement history
    logs = Measurement.query.filter_by(
        user_id=current_user.id,
        type=measurement_type
    ).order_by(Measurement.date.desc()).all()
    
    return render_template(
        'workout/track_measurement.html',
        measurement_type=measurement_type,
        logs=logs,
        limits=valid_types[measurement_type]
    )

@workout.route('/api/weight-data')
@login_required
def get_weight_data():
    range_param = request.args.get('range', '3m')
    
    # Calculate the date range
    now = datetime.utcnow()
    if range_param == '3m':
        start_date = now - timedelta(days=90)
    elif range_param == '6m':
        start_date = now - timedelta(days=180)
    elif range_param == 'cy':
        # Get first day of current year
        start_date = datetime(now.year, 1, 1)
    else:  # all time
        start_date = datetime.min
    
    # Get weight logs for the selected period
    logs = Measurement.query.filter(
        Measurement.user_id == current_user.id,
        Measurement.type == 'weight',
        Measurement.date >= start_date
    ).order_by(Measurement.date).all()
    
    # Format data for Chart.js
    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    values = [float(log.value) for log in logs]
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@workout.route('/api/measurement-data/<measurement_type>')
@login_required
def get_measurement_data(measurement_type):
    range_param = request.args.get('range', '3m')
    
    # Calculate the date range
    now = datetime.utcnow()
    if range_param == '3m':
        start_date = now - timedelta(days=90)
    elif range_param == '6m':
        start_date = now - timedelta(days=180)
    elif range_param == 'cy':
        # Get first day of current year
        start_date = datetime(now.year, 1, 1)
    else:  # all time
        start_date = datetime.min
    
    # Get logs for the selected period
    logs = Measurement.query.filter(
        Measurement.user_id == current_user.id,
        Measurement.type == measurement_type,
        Measurement.date >= start_date
    ).order_by(Measurement.date).all()
    
    # Format data for Chart.js
    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    
    # Convert values to preferred units and round to 2 decimal places
    if measurement_type == 'weight':
        if current_user.preferred_weight_unit == 'lbs':
            values = [round(float(log.value * 2.20462), 2) for log in logs]  # Round to 2 decimal places
        else:
            values = [round(float(log.value), 2) for log in logs]  # Round to 2 decimal places
    else:
        if current_user.preferred_measurement_unit == 'in':
            values = [round(float(log.value * 0.393701), 2) for log in logs]  # Round to 2 decimal places
        else:
            values = [round(float(log.value), 2) for log in logs]  # Round to 2 decimal places
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@workout.route('/measurements/<measurement_type>', methods=['POST'])
@login_required
def log_measurement(measurement_type):
    data = request.get_json()
    value = data.get('value')
    unit = data.get('unit')
    
    valid_types = {
        'weight': {'unit': 'kg', 'min': 5, 'max': 600},
        'body_fat': {'unit': '%', 'min': 1, 'max': 50},
        'chest': {'unit': 'cm', 'min': 50, 'max': 200},
        'waist': {'unit': 'cm', 'min': 40, 'max': 200},
        'hips': {'unit': 'cm', 'min': 50, 'max': 200},
        'neck': {'unit': 'cm', 'min': 20, 'max': 100},
        'left_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'right_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'left_calf': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_calf': {'unit': 'cm', 'min': 10, 'max': 100}
    }
    
    if measurement_type not in valid_types:
        return jsonify({'success': False, 'error': 'Invalid measurement type'}), 400
        
    # Convert value based on unit
    try:
        value = float(value)
        
        # Import unit conversion utilities
        from .utils import normalize_weight_to_kg, normalize_measurement_to_cm
        
        # Store in kg and cm regardless of input unit
        if unit == 'lbs':
            value = normalize_weight_to_kg(value, 'lbs')
        elif unit == 'in':
            value = normalize_measurement_to_cm(value, 'in')
            
        # Validate converted value (always in standard unit - kg or cm)
        if value < valid_types[measurement_type]['min'] or value > valid_types[measurement_type]['max']:
            # For display purposes, convert the min/max back to user's preferred unit
            min_val = valid_types[measurement_type]['min']
            max_val = valid_types[measurement_type]['max']
            
            if unit == 'lbs':
                from .utils import convert_weight
                min_val = convert_weight(min_val, 'kg', 'lbs')
                max_val = convert_weight(max_val, 'kg', 'lbs')
            elif unit == 'in':
                from .utils import convert_measurement
                min_val = convert_measurement(min_val, 'cm', 'in')
                max_val = convert_measurement(max_val, 'cm', 'in')
                
            return jsonify({
                'success': False, 
                'error': f"Value must be between {min_val} and {max_val} {unit}"
            }), 400
            
        # Save the measurement (always stored in kg or cm)
        measurement = Measurement(
            user_id=current_user.id,
            type=measurement_type,
            value=value,
            date=datetime.utcnow(),
            unit=valid_types[measurement_type]['unit']  # Store the standard unit (kg or cm)
        )
        db.session.add(measurement)
        db.session.commit()
        
        # Pass back the formatted value according to user's preferences
        if measurement_type == 'weight' and current_user.preferred_weight_unit == 'lbs':
            from .utils import convert_weight
            display_value = convert_weight(value, 'kg', 'lbs')
            display_unit = 'lbs'
        elif measurement_type != 'weight' and measurement_type != 'body_fat' and current_user.preferred_measurement_unit == 'in':
            from .utils import convert_measurement
            display_value = convert_measurement(value, 'cm', 'in')
            display_unit = 'in'
        else:
            display_value = value
            display_unit = valid_types[measurement_type]['unit']
        
        return jsonify({
            'success': True,
            'message': f'{measurement_type.replace("_", " ").title()} logged successfully',
            'measurement': {
                'id': measurement.id,
                'type': measurement_type,
                'value': display_value,
                'unit': display_unit,
                'date': measurement.date.strftime('%B %d, %Y %H:%M')
            }
        })
    except (TypeError, ValueError) as e:
        return jsonify({'success': False, 'error': f'Invalid value: {str(e)}'}), 400

@workout.route('/delete-measurement/<int:log_id>', methods=['DELETE'])
@login_required
def delete_measurement(log_id):
    """Delete a specific measurement log."""
    log = Measurement.query.get_or_404(log_id)

    if log.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if log.type == 'weight' and Measurement.query.filter_by(user_id=current_user.id, type='weight').count() <= 1:
        return jsonify({'success': False, 'error': 'You must have at least one weight logged at all times'}), 400

    try:
        db.session.delete(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@workout.route('/api/exercise-ranges/<int:exercise_id>', methods=['POST'])
@login_required
def update_exercise_ranges(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    data = request.get_json()
    
    try:
        print(f"Received data: {data}")  # Add debug logging
        
        # Update range values
        if 'min_reps' in data and 'max_reps' in data:
            min_reps = data.get('min_reps')
            max_reps = data.get('max_reps')
            
            # Convert to integers if not None
            if min_reps is not None:
                exercise.min_reps = int(min_reps) 
            else:
                exercise.min_reps = None
                
            if max_reps is not None:
                exercise.max_reps = int(max_reps)
            else:
                exercise.max_reps = None
                
        if 'min_duration' in data and 'max_duration' in data:
            min_duration = data.get('min_duration')
            max_duration = data.get('max_duration')
            
            # Convert to integers if not None
            if min_duration is not None:
                exercise.min_duration = int(min_duration)
            else:
                exercise.min_duration = None
                
            if max_duration is not None:
                exercise.max_duration = int(max_duration)
            else:
                exercise.max_duration = None
                
        if 'min_distance' in data and 'max_distance' in data:
            min_distance = data.get('min_distance')
            max_distance = data.get('max_distance')
            
            # Convert to float if not None
            if min_distance is not None:
                exercise.min_distance = float(min_distance)
            else:
                exercise.min_distance = None
                
            if max_distance is not None:
                exercise.max_distance = float(max_distance)
            else:
                exercise.max_distance = None
        
        # Set range_enabled from the request data
        if 'range_enabled' in data:
            exercise.range_enabled = bool(data.get('range_enabled'))
        
        # Validate ranges
        if exercise is not None and exercise.range_enabled:
            if exercise.min_reps is not None and exercise.max_reps is not None:
                if exercise.min_reps > exercise.max_reps:
                    return jsonify({'success': False, 'error': 'Minimum reps cannot be greater than maximum reps'})
                    
            if exercise.min_duration is not None and exercise.max_duration is not None:
                if exercise.min_duration > exercise.max_duration:
                    return jsonify({'success': False, 'error': 'Minimum duration cannot be greater than maximum duration'})
                    
            if exercise.min_distance is not None and exercise.max_distance is not None:
                if exercise.min_distance > exercise.max_distance:
                    return jsonify({'success': False, 'error': 'Minimum distance cannot be greater than maximum distance'})
        
        db.session.commit()
        print(f"Updated exercise ranges for {exercise.id}: range_enabled={exercise.range_enabled}, min_reps={exercise.min_reps}, max_reps={exercise.max_reps}")
        
        return jsonify({
            'success': True,
            'range_enabled': exercise.range_enabled,
            'min_reps': exercise.min_reps,
            'max_reps': exercise.max_reps,
            'min_duration': exercise.min_duration,
            'max_duration': exercise.max_duration,
            'min_distance': exercise.min_distance,
            'max_distance': exercise.max_distance
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating exercise ranges: {str(e)}")  # Add logging
        return jsonify({'success': False, 'error': str(e)})

@workout.route('/api/exercise-rest/<int:exercise_id>', methods=['POST'])
@login_required
def update_exercise_rest(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    data = request.get_json()
    
    try:
        print(f"Received rest duration data for exercise {exercise_id} ({exercise.name}): {data}")
        
        # Update rest duration
        if 'rest_duration' in data:
            rest_duration = data.get('rest_duration')
            
            # Convert to integer if not None
            if rest_duration is not None:
                exercise.rest_duration = int(rest_duration)
            else:
                exercise.rest_duration = None
        
        db.session.commit()
        print(f"Updated exercise rest duration for {exercise.id} ({exercise.name}): rest_duration={exercise.rest_duration}")
        
        return jsonify({
            'success': True,
            'rest_duration': exercise.rest_duration
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating exercise rest duration: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@workout.route('/workout')
@login_required
def workout_page():
    """Display the user's workouts and routines"""
    routines = Routine.query.filter_by(user_id=current_user.id).all()
    
    # Process routines to add exercise count
    for routine in routines:
        try:
            if routine.exercises:
                exercises_data = json.loads(routine.exercises)
                routine.exercise_count = len(exercises_data) if isinstance(exercises_data, list) else 0
            else:
                routine.exercise_count = 0
        except:
            routine.exercise_count = 0
    
    return render_template('workout/workout.html', routines=routines)

@workout.route('/routine/create')
@login_required
def create_routine():
    # Get all exercises for display
    exercises = Exercise.query.all()
    
    return render_template('workout/create_routine.html', 
                          exercises=exercises,
                          is_edit=False)

@workout.route('/routine/<int:routine_id>')
@login_required
def view_routine(routine_id):
    routine = Routine.query.filter_by(id=routine_id).first_or_404()
    
    # Check if user can view this routine
    if not routine.is_public and routine.user_id != current_user.id:
        flash('You do not have permission to view this routine.', 'danger')
        return redirect(url_for('workout.workout_page'))
    
    # Get the creator's username
    creator = User.query.get(routine.user_id)
    creator_name = creator.username if creator else "Unknown"
    
    # Parse routine exercises
    exercises = []
    if routine.exercises:
        try:
            routine_exercises = json.loads(routine.exercises)
            for exercise_data in routine_exercises:
                exercise_id = exercise_data.get('id')
                if exercise_id:
                    exercise = Exercise.query.get(exercise_id)
                    if exercise:
                        exercises.append({
                            'id': exercise.id,
                            'name': exercise.name,
                            'muscles_worked': exercise.muscles_worked,
                            'input_type': exercise.input_type,
                            'sets': exercise_data.get('sets', [])
                        })
        except Exception as e:
            app.logger.error(f"Error parsing routine exercises: {str(e)}")
    
    return render_template('workout/view_routine.html', 
                          routine=routine,
                          creator_name=creator_name,
                          exercises=exercises)

@workout.route('/routine/<int:routine_id>/edit')
@login_required
def edit_routine(routine_id):
    routine = Routine.query.filter_by(id=routine_id).first_or_404()
    
    # Check if user can edit this routine
    if routine.user_id != current_user.id:
        flash('You do not have permission to edit this routine.', 'danger')
        return redirect(url_for('workout.workout_page'))
    
    # Get all exercises for display
    exercises = Exercise.query.all()
    
    return render_template('workout/create_routine.html', 
                          routine=routine,
                          exercises=exercises,
                          is_edit=True)

@workout.route('/routine/<int:routine_id>/perform')
@login_required
def perform_routine(routine_id):
    routine = Routine.query.filter_by(id=routine_id).first_or_404()
    
    # Check if user can access this routine
    if not routine.is_public and routine.user_id != current_user.id:
        flash('You do not have permission to view this routine.', 'danger')
        return redirect(url_for('workout.workout_page'))
    
    # Get all exercises for display
    exercises = Exercise.query.all()
    
    # Prepare routine data for JS
    routine_data = {
        'id': routine.id,
        'name': routine.name,
        'level': routine.level,
        'goal': routine.goal,
        'muscle_groups': routine.muscle_groups,
        'description': routine.description,
        'exercises': []
    }
    
    # Parse exercises from the routine's JSON
    if routine.exercises:
        try:
            routine_exercises = json.loads(routine.exercises)
            routine_data['exercises'] = routine_exercises
        except:
            routine_data['exercises'] = []
    
    # Convert to JSON for template
    routine_json = json.dumps(routine_data)
    
    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    user_weight = latest_bodyweight.value if latest_bodyweight else None
    
    return render_template('workout/perform_routine.html', 
                          routine=routine, 
                          exercises=exercises,
                          routine_json=routine_json,
                          user_weight=user_weight)

@workout.route('/api/routines', methods=['GET'])
@login_required
def get_routines():
    """
    Get all routines for the current user.
    """
    routines = Routine.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'routines': [routine.to_dict() for routine in routines]
    })

@workout.route('/api/routines', methods=['POST'])
@login_required
def create_routine_api():
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Routine name is required'})
    
    # Create and save the routine
    new_routine = Routine(
        user_id=current_user.id,
        name=data.get('name'),
        level=data.get('level', 'Intermediate'),
        goal=data.get('goal', 'General Fitness'),
        muscle_groups=','.join(data.get('muscle_groups', [])),
        description=data.get('description', ''),
        is_public=data.get('is_public', False),
        exercises=json.dumps(data.get('exercises', [])),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.session.add(new_routine)
    db.session.commit()
    
    return jsonify({'success': True, 'routine_id': new_routine.id})

@workout.route('/api/routines/<int:routine_id>', methods=['GET'])
@login_required
def get_routine(routine_id):
    """Get a routine by ID"""
    routine = Routine.query.get_or_404(routine_id)
    
    # Check if user has access to this routine
    if routine.user_id != current_user.id and not routine.is_public:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to view this routine'
        }), 403
        
    creator = User.query.get(routine.user_id)
    
    return jsonify({
        'success': True,
        'routine': routine.to_dict(),
        'creator': {
            'id': creator.id,
            'username': creator.username
        },
        'is_owner': routine.user_id == current_user.id
    })

@workout.route('/api/routines/<int:routine_id>', methods=['PUT'])
@login_required
def update_routine_api(routine_id):
    routine = Routine.query.filter_by(id=routine_id).first_or_404()
    
    # Check if user can edit this routine
    if routine.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You do not have permission to edit this routine'})
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Routine name is required'})
    
    # Check if sharing status changed from private to public
    was_public = routine.is_public
    is_public_now = data.get('is_public', False)
    
    print(f"Routine {routine.id} update: was_public={was_public}, is_public_now={is_public_now}")
    
    # Update the routine
    routine.name = data.get('name')
    routine.level = data.get('level', routine.level)
    routine.goal = data.get('goal', routine.goal)
    routine.muscle_groups = ','.join(data.get('muscle_groups', []))
    routine.description = data.get('description', '')
    routine.is_public = is_public_now
    routine.exercises = json.dumps(data.get('exercises', []))
    routine.updated_at = datetime.now()
    
    # If the routine is now public, we need to create or update the shared version
    if is_public_now:
        # Check if there's already a shared version
        shared_routine = SharedRoutine.query.filter_by(original_id=routine.id).first()
        
        print(f"Checking shared routine for routine {routine.id}: exists={shared_routine is not None}")
        
        if shared_routine:
            # Update the existing shared version
            print(f"Updating existing shared routine {shared_routine.id}")
            shared_routine.name = routine.name
            shared_routine.level = routine.level
            shared_routine.goal = routine.goal
            shared_routine.muscle_groups = routine.muscle_groups
            shared_routine.description = routine.description
            shared_routine.exercises = routine.exercises
            db.session.commit()
            print(f"Shared routine updated successfully")
        else:
            # Create a new shared version
            print(f"Creating new shared routine for routine {routine.id}")
            shared_routine = SharedRoutine(
                original_id=routine.id,
                name=routine.name,
                level=routine.level,
                goal=routine.goal,
                muscle_groups=routine.muscle_groups,
                description=routine.description,
                exercises=routine.exercises,
                user_id=routine.user_id,
                created_at=datetime.now(),
                copy_count=0
            )
            db.session.add(shared_routine)
            db.session.commit()
            print(f"New shared routine created with ID {shared_routine.id}")
    elif not is_public_now and was_public:
        # If the routine is no longer public, we might want to keep the shared version
        # but update it to reflect the latest state before it was made private
        shared_routine = SharedRoutine.query.filter_by(original_id=routine.id).first()
        if shared_routine:
            print(f"Routine is now private but keeping shared version {shared_routine.id}")
    
    return jsonify({'success': True, 'routine_id': routine.id})

@workout.route('/api/routines/<int:routine_id>', methods=['DELETE'])
@login_required
def delete_routine_api(routine_id):
    routine = Routine.query.filter_by(id=routine_id).first_or_404()
    
    # Check if user can delete this routine
    if routine.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You do not have permission to delete this routine'})
    
    db.session.delete(routine)
    db.session.commit()
    
    return jsonify({'success': True})

@workout.route('/api/routines', methods=['GET'])
@login_required
def get_user_routines():
    """Get routines for current user"""
    routines = Routine.query.filter_by(user_id=current_user.id).order_by(Routine.updated_at.desc()).all()
    
    return jsonify({
        'success': True,
        'routines': [routine.to_dict() for routine in routines]
    })

@workout.route('/api/routines/explore', methods=['GET'])
@login_required
def get_explore_routines():
    """Get public routines for exploration from the shared routines table"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get filter parameters
    level = request.args.get('level')
    goal = request.args.get('goal')
    muscle_group = request.args.get('muscle_group')
    
    # Build query
    query = SharedRoutine.query
    
    # Apply filters
    if level:
        query = query.filter(SharedRoutine.level == level)
    if goal:
        query = query.filter(SharedRoutine.goal == goal)
    if muscle_group:
        query = query.filter(SharedRoutine.muscle_groups.like(f'%{muscle_group}%'))
    
    # Get paginated results
    pagination = query.order_by(SharedRoutine.copy_count.desc(), SharedRoutine.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    routines = pagination.items
    
    # Format routines for response
    routine_data = []
    for routine in routines:
        creator = User.query.get(routine.user_id)
        try:
            exercises = json.loads(routine.exercises) if routine.exercises else []
            exercise_count = len(exercises)
        except:
            exercise_count = 0
            
        routine_data.append({
            'id': routine.id,
            'name': routine.name,
            'level': routine.level,
            'goal': routine.goal,
            'muscle_groups': routine.muscle_groups.split(',') if routine.muscle_groups else [],
            'description': routine.description,
            'exercises': routine.exercises,
            'exercise_count': exercise_count,
            'copy_count': routine.copy_count or 0,
            'creator': {
                'id': creator.id if creator else 0,
                'username': creator.username if creator else "Unknown"
            }
        })
    
    return jsonify({
        'success': True,
        'routines': routine_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@workout.route('/explore')
@login_required
def explore_routines():
    """Render the explore routines page"""
    return render_template('workout/explore_routines.html',
                         levels=WORKOUT_LEVELS,
                         goals=WORKOUT_GOALS,
                         muscle_groups=MUSCLE_GROUPS)

@workout.route('/api/routines/explore/<int:shared_id>/copy', methods=['POST'])
@login_required
def copy_shared_routine(shared_id):
    """Copy a shared routine to user's routines"""
    shared_routine = SharedRoutine.query.get_or_404(shared_id)
    
    try:
        # Create a copy of the routine for the current user
        new_routine = Routine(
            name=f"{shared_routine.name} (Copy)",
            level=shared_routine.level,
            goal=shared_routine.goal,
            muscle_groups=shared_routine.muscle_groups,
            exercises=shared_routine.exercises,
            is_public=False,  # Default to private for copied routines
            description=shared_routine.description,
            user_id=current_user.id
        )
        
        # Increment the copy count
        shared_routine.copy_count += 1
        
        db.session.add(new_routine)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'routine_id': new_routine.id,
            'message': 'Routine copied successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error copying routine: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to copy routine'
        }), 500

@workout.route('/api/workouts/<int:workout_id>/exercises', methods=['POST'])
@login_required
def add_exercise_to_workout(workout_id):
    """Add an exercise to a workout from a routine"""
    workout = Workout.query.get_or_404(workout_id)
    
    # Check if user has permission to modify this workout
    if workout.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to modify this workout'
        }), 403
    
    data = request.json
    exercise_id = data.get('exercise_id')
    sets_data = data.get('sets', [])
    
    if not exercise_id:
        return jsonify({
            'success': False,
            'error': 'Exercise ID is required'
        }), 400
    
    # Get the exercise details
    exercise = Exercise.query.get_or_404(exercise_id)
    
    try:
        # Create WorkoutExercise record
        workout_exercise = WorkoutExercise(
            workout_id=workout_id,
            exercise_id=exercise_id,
            order=len(workout.exercises) + 1  # Add to the end
        )
        db.session.add(workout_exercise)
        db.session.flush()  # Flush to get the ID
        
        # Add sets for this exercise
        for i, set_data in enumerate(sets_data):
            if exercise.input_type == 'weight_reps':
                weight = set_data.get('weight', 0)
                reps = set_data.get('reps', 0)
                rest = set_data.get('rest', 60)
                
                workout_set = WorkoutSet(
                    workout_exercise_id=workout_exercise.id,
                    set_number=i + 1,
                    weight=weight,
                    reps=reps,
                    rest_duration=rest
                )
                db.session.add(workout_set)
                
            elif exercise.input_type == 'bodyweight_reps':
                reps = set_data.get('reps', 0)
                rest = set_data.get('rest', 60)
                
                workout_set = WorkoutSet(
                    workout_exercise_id=workout_exercise.id,
                    set_number=i + 1,
                    reps=reps,
                    rest_duration=rest
                )
                db.session.add(workout_set)
                
            elif exercise.input_type == 'duration':
                duration = set_data.get('duration', 0)
                rest = set_data.get('rest', 60)
                
                workout_set = WorkoutSet(
                    workout_exercise_id=workout_exercise.id,
                    set_number=i + 1,
                    duration=duration,
                    rest_duration=rest
                )
                db.session.add(workout_set)
                
            elif exercise.input_type == 'distance_duration':
                distance = set_data.get('distance', 0)
                duration = set_data.get('duration', 0)
                rest = set_data.get('rest', 60)
                
                workout_set = WorkoutSet(
                    workout_exercise_id=workout_exercise.id,
                    set_number=i + 1,
                    distance=distance,
                    duration=duration,
                    rest_duration=rest
                )
                db.session.add(workout_set)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {exercise.name} to workout'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding exercise to workout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add exercise to workout'
        }), 500

@workout.route('/workout/perform/<int:workout_id>')
@login_required
def perform_workout(workout_id):
    """Perform an active workout"""
    workout = Workout.query.get_or_404(workout_id)
    
    # Check if user has permission to perform this workout
    if workout.user_id != current_user.id:
        flash('You do not have permission to perform this workout.', 'error')
        return redirect(url_for('workout.workout_page'))
    
    # Check if workout is already completed
    if workout.completed:
        flash('This workout is already completed.', 'info')
        return redirect(url_for('workout.workout_page'))
    
    # Get workout exercises and sets
    workout_exercises = WorkoutExercise.query.filter_by(workout_id=workout_id).order_by(WorkoutExercise.order).all()
    
    # Prepare exercises data for the template
    exercises_data = []
    for we in workout_exercises:
        exercise = Exercise.query.get(we.exercise_id)
        sets = WorkoutSet.query.filter_by(workout_exercise_id=we.id).order_by(WorkoutSet.set_number).all()
        
        exercises_data.append({
            'id': we.id,
            'exercise_id': exercise.id,
            'name': exercise.name,
            'muscles_worked': exercise.muscles_worked,
            'input_type': exercise.input_type,
            'sets': [s.to_dict() for s in sets]
        })
    
    return render_template('workout/perform_workout.html',
                          workout=workout,
                          exercises=exercises_data)

@workout.route('/api/sets/<int:set_id>', methods=['PUT'])
@login_required
def update_set(set_id):
    """Update a set's data"""
    workout_set = WorkoutSet.query.get_or_404(set_id)
    
    # Check if user has permission to update this set
    workout_exercise = WorkoutExercise.query.get(workout_set.workout_exercise_id)
    workout = Workout.query.get(workout_exercise.workout_id)
    
    if workout.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to update this set'
        }), 403
    
    data = request.json
    
    try:
        # Update set data based on what was provided
        if 'weight' in data:
            workout_set.weight = data['weight']
        if 'reps' in data:
            workout_set.reps = data['reps']
        if 'duration' in data:
            workout_set.duration = data['duration']
        if 'distance' in data:
            workout_set.distance = data['distance']
        if 'additional_weight' in data:
            workout_set.additional_weight = data['additional_weight']
        if 'assistance_weight' in data:
            workout_set.assistance_weight = data['assistance_weight']
        if 'rest_duration' in data:
            workout_set.rest_duration = data['rest_duration']
        
        # Mark as completed if requested
        if 'completed' in data and data['completed']:
            workout_set.completed = True
            workout_set.completion_time = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Set updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating set: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update set'
        }), 500

@workout.route('/api/exercises/<int:exercise_id>/sets', methods=['POST'])
@login_required
def add_set(exercise_id):
    """Add a new set to a workout exercise"""
    workout_exercise = WorkoutExercise.query.get_or_404(exercise_id)
    
    # Check if user has permission to modify this workout
    workout = Workout.query.get(workout_exercise.workout_id)
    
    if workout.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to modify this workout'
        }), 403
    
    data = request.json
    
    try:
        # Create a new set
        new_set = WorkoutSet(
            workout_exercise_id=exercise_id,
            set_number=data.get('set_number', 1),
            rest_duration=data.get('rest_duration', 60)
        )
        
        db.session.add(new_set)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'set_id': new_set.id,
            'message': 'Set added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding set: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add set'
        }), 500

@workout.route('/api/workouts/<int:workout_id>/complete', methods=['POST'])
@login_required
def complete_workout(workout_id):
    """Mark a workout as completed"""
    workout = Workout.query.get_or_404(workout_id)
    
    # Check if user has permission to modify this workout
    if workout.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to modify this workout'
        }), 403
    
    data = request.json
    
    try:
        # Mark workout as completed - check if the column exists
        try:
            workout.completed = True
        except Exception as e:
            print(f"Warning: Could not set completed field: {str(e)}")
            # Continue without setting this field
            
        # Set end time - check if the column exists
        try:
            workout.end_time = datetime.utcnow()
        except Exception as e:
            print(f"Warning: Could not set end_time field: {str(e)}")
            # Continue without setting this field
            
        # Calculate duration in seconds if start_time exists
        try:
            if hasattr(workout, 'start_time') and workout.start_time:
                duration = (workout.end_time - workout.start_time).total_seconds()
                # Store the timer duration in data for later comparison with exercise durations
                if data and isinstance(data, dict):
                    data['duration'] = int(duration)
        except Exception as e:
            print(f"Warning: Could not calculate duration: {str(e)}")
        
        # Save any notes
        if 'notes' in data:
            workout.notes = data['notes']
        
        # Parse workout data and update it
        workout_data = {}
        if workout.data:
            try:
                workout_data = json.loads(workout.data)
                # Merge updated data
                if data and isinstance(data, dict):
                    for key, value in data.items():
                        workout_data[key] = value
            except Exception as e:
                print(f"Error parsing workout data: {e}")
                workout_data = data if data else {}
        else:
            workout_data = data if data else {}
        
        # Save updated workout data
        workout.data = json.dumps(workout_data)
        
        # Calculate metrics with our helper function
        metrics = calculate_workout_metrics(workout_data)
        
        # Update workout metrics
        workout.volume = metrics['volume']
        workout.duration = metrics['duration']
        workout.rating = data.get('rating', metrics['rating'])
        
        # Award XP to the user
        # Base XP for workout
        exp_gained = 10
        
        # Additional XP based on completed sets
        completed_sets = 0
        for we in workout.exercises:
            completed_sets += sum(1 for s in we.sets if s.completed)
        
        # If no sets from relationships, check the workout data
        if completed_sets == 0 and workout_data and 'exercises' in workout_data:
            for exercise in workout_data['exercises']:
                if 'sets' in exercise:
                    completed_sets += sum(1 for s in exercise['sets'] if s.get('completed', False))
        
        exp_gained += completed_sets * 3
        
        # Additional XP for workout duration and volume
        if workout.duration:
            # Extra XP for every 10 minutes
            exp_gained += (workout.duration // 600) * 5
            
        # Additional XP for volume
        if workout.volume:
            # Extra XP for every 1000kg of volume
            exp_gained += (workout.volume // 1000) * 10
        
        # Create a Session object to store this workout's history
        new_session = Session(
            user_id=current_user.id,
            session_date=workout.end_time or datetime.utcnow(),
            duration=str(workout.duration) if workout.duration else "0",
            volume=workout.volume,
            exp_gained=exp_gained,
            session_rating=workout.rating,
            title=workout.title or "Workout",
            description=workout.notes,
            sets_completed=completed_sets
        )
        db.session.add(new_session)
        db.session.flush()  # Get the ID without committing
        
        print(f"Created session with ID {new_session.id}")
        
        # Convert WorkoutSet objects to Set objects to store in the exercise history
        for workout_exercise in workout.exercises:
            exercise_id = workout_exercise.exercise_id
            exercise = Exercise.query.get(exercise_id)
            
            if not exercise:
                continue
                
            completed_workout_sets = [s for s in workout_exercise.sets if s.completed]
            
            for i, workout_set in enumerate(completed_workout_sets):
                # Create a new Set for the history
                new_set = Set(
                    exercise_id=exercise_id,
                    session_id=new_session.id,
                    completed=True,
                    order=i,
                    set_type='normal'
                )
                
                # Copy all the exercise-specific fields
                if workout_set.weight is not None:
                    new_set.weight = workout_set.weight
                
                if workout_set.reps is not None:
                    new_set.reps = workout_set.reps
                
                if workout_set.duration is not None:
                    new_set.time = workout_set.duration  # Note: different field name
                
                if workout_set.distance is not None:
                    new_set.distance = workout_set.distance
                
                if workout_set.additional_weight is not None:
                    new_set.additional_weight = workout_set.additional_weight
                
                if workout_set.assistance_weight is not None:
                    new_set.assistance_weight = workout_set.assistance_weight
                
                # Calculate volume based on exercise type
                if exercise.input_type == 'weight_reps' and workout_set.weight and workout_set.reps:
                    new_set.volume = workout_set.weight * workout_set.reps
                elif exercise.input_type == 'duration' and workout_set.duration:
                    new_set.volume = workout_set.duration  # Volume is time for duration exercises
                elif exercise.input_type == 'duration_weight' and workout_set.weight and workout_set.duration:
                    new_set.volume = workout_set.weight * workout_set.duration / 60  # Weight * minutes
                elif exercise.input_type == 'distance_duration' and workout_set.distance and workout_set.duration:
                    new_set.volume = workout_set.distance * workout_set.duration / 60  # Distance * minutes
                elif exercise.input_type == 'weighted_bodyweight' and workout_set.additional_weight and workout_set.reps:
                    # For weighted bodyweight, use current user's bodyweight + added weight
                    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
                        .order_by(Measurement.date.desc()).first()
                    bodyweight = latest_bodyweight.value if latest_bodyweight else 70  # Default to 70kg
                    new_set.volume = (bodyweight + workout_set.additional_weight) * workout_set.reps
                
                # Check if the set was within the exercise's target range (if set)
                if exercise is not None and exercise.range_enabled:
                    new_set.within_range = new_set.check_within_range()
                
                db.session.add(new_set)
                
            print(f"Added {len(completed_workout_sets)} sets for exercise {exercise.name}")
        
        # Update user stats
        current_user.exp += exp_gained
        current_user.update_level()
        
        # Update streak if it's a new day
        today = datetime.now().date()
        last_workout_date = None
        
        # Find the date of the last workout - handle case where completed field might not exist
        try:
            last_workout = Workout.query.filter_by(
                user_id=current_user.id, 
                completed=True
            ).order_by(Workout.end_time.desc()).first()
        except Exception as e:
            print(f"Warning: Could not query with completed field: {str(e)}")
            # Fall back to just getting the most recent workout by end_time
            try:
                last_workout = Workout.query.filter_by(
                    user_id=current_user.id
                ).filter(Workout.end_time.isnot(None)).order_by(Workout.end_time.desc()).first()
            except Exception as e2:
                print(f"Warning: Could not query with end_time either: {str(e2)}")
                # Final fallback to just getting by date
                last_workout = Workout.query.filter_by(
                    user_id=current_user.id
                ).order_by(Workout.date.desc()).first()
        
        if last_workout and last_workout.end_time:
            last_workout_date = last_workout.end_time.date()
        
        # Update streak
        if not last_workout_date or last_workout_date < today:
            # Check if the last workout was yesterday
            if last_workout_date and (today - last_workout_date).days == 1:
                current_user.streak += 1
            # If it's been more than a day, reset streak
            elif last_workout_date and (today - last_workout_date).days > 1:
                current_user.streak = 1
            # If it's their first workout
            else:
                current_user.streak = 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"Workout completed successfully: {workout.id}")
        
        return jsonify({
            'success': True,
            'message': 'Workout completed successfully',
            'exp_gained': exp_gained,
            'new_streak': current_user.streak,
            'session_id': workout.id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error completing workout: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to complete workout: {str(e)}'
        }), 500

@workout.route('/api/log-workout', methods=['POST'])
@login_required
def log_workout_api():
    """API endpoint for logging a workout"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Import unit conversion utilities
        from .utils import normalize_weight_to_kg, normalize_distance_to_km

        # Get user preferences
        weight_unit = current_user.preferred_weight_unit
        distance_unit = current_user.preferred_distance_unit
        is_imperial = weight_unit == 'lbs'

        # Process exercises to ensure IDs are integers and add necessary data
        if 'exercises' in data:
            for exercise in data['exercises']:
                if 'id' in exercise:
                    # Make sure ID is stored as integer
                    exercise['id'] = int(str(exercise['id']))
                    print(f"Processed exercise ID: {exercise['id']} ({type(exercise['id'])})")
                    
                    # Get actual exercise info to check type
                    ex = Exercise.query.get(exercise['id'])
                    if ex and ex.input_type == 'duration_weight':
                        print(f"Processing duration_weight exercise: {ex.name}")
                        
                        # Special handling for planks
                        is_plank = 'plank' in ex.name.lower()
                        
                        # Store default values at the exercise level
                        if 'defaults' not in exercise:
                            exercise['defaults'] = {}
                            
                        # Ensure defaults exist for planks
                        if is_plank:
                            # Get defaults from the exercise or set reasonable defaults
                            weight = exercise.get('weight', 0)
                            duration = exercise.get('time', 0) or exercise.get('duration', 0) 
                            
                            # Use a minimum default duration for planks if none provided
                            if not duration:
                                duration = 60  # Default to 60 seconds
                                print(f"Setting default duration for plank to {duration} seconds")
                            
                            # Set defaults
                            exercise['defaults']['weight'] = weight
                            exercise['defaults']['time'] = duration
                            print(f"Added defaults for {ex.name}: weight={weight}, time={duration}")

                # Process each set to store data properly
                if 'sets' in exercise:
                    for set_data in exercise['sets']:
                        if set_data.get('completed', False):
                            # Make sure each set has a data dictionary
                            if 'data' not in set_data:
                                set_data['data'] = {}
                            
                            # Convert units to standard units (kg, km) before storage
                            # Weight conversions
                            if 'weight' in set_data and is_imperial:
                                set_data['weight'] = normalize_weight_to_kg(float(set_data['weight']), 'lbs')
                                
                            if 'additional_weight' in set_data and is_imperial:
                                set_data['additional_weight'] = normalize_weight_to_kg(float(set_data['additional_weight']), 'lbs')
                                
                            if 'assistance_weight' in set_data and is_imperial:
                                set_data['assistance_weight'] = normalize_weight_to_kg(float(set_data['assistance_weight']), 'lbs')
                                
                            # Distance conversions
                            if 'distance' in set_data and distance_unit == 'mi':
                                set_data['distance'] = normalize_distance_to_km(float(set_data['distance']), 'mi')
                            
                            # Store weight, reps, time, etc. in the data dictionary
                            for field in ['weight', 'reps', 'time', 'duration', 'distance', 'userWeight', 'additional_weight', 'assistance_weight']:
                                if field in set_data:
                                    set_data['data'][field] = set_data[field]
                            
                            # Special handling for plank exercises
                            if ex and 'plank' in ex.name.lower():
                                # If time is missing, use default
                                if not set_data.get('time') and not set_data.get('duration'):
                                    if 'defaults' in exercise and 'time' in exercise['defaults']:
                                        default_time = exercise['defaults']['time']
                                        set_data['time'] = default_time
                                        set_data['data']['time'] = default_time
                                        print(f"Using default time {default_time}s for plank set")
                                
                                # Store user weight in the set
                                if 'userWeight' in set_data:
                                    user_weight = set_data['userWeight']
                                    if is_imperial:
                                        user_weight = normalize_weight_to_kg(float(user_weight), 'lbs')
                                    print(f"User weight for plank: {user_weight}kg")
                                    set_data['userWeight'] = user_weight
                                    set_data['data']['userWeight'] = user_weight
                                
                            # Calculate volume for weight/reps exercises if not provided
                            if 'volume' not in set_data:
                                ex_id = exercise.get('id')
                                if ex_id:
                                    ex = Exercise.query.get(ex_id)
                                    if ex:
                                        # Get user's bodyweight for bodyweight exercises
                                        user_weight = None
                                        if ex.input_type in ['bodyweight_reps', 'weighted_bodyweight', 'assisted_bodyweight']:
                                            latest_weight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
                                                .order_by(Measurement.date.desc()).first()
                                            user_weight = latest_weight.value if latest_weight else 70
                                            
                                        # Calculate volume using the utility method
                                        volume = ex.calculate_volume(set_data, bodyweight=user_weight, user=current_user)
                                        if volume:
                                            set_data['volume'] = volume
                                            print(f"Calculated volume for set: {volume}")

        # Calculate metrics with our helper function
        metrics = calculate_workout_metrics(data)

        # Create new workout
        workout = Workout(
            user_id=current_user.id,
            title=data.get('title', 'Workout'),
            date=datetime.utcnow(),
            data=json.dumps(data),
            volume=metrics['volume'],
            duration=metrics['duration'],
            rating=data.get('rating', metrics['rating']),
            start_time=datetime.utcnow(),  # Set start time
            completed=False  # Not completed yet
        )
        db.session.add(workout)
        db.session.flush()  # Get the ID without committing

        print(f"Workout saved with ID: {workout.id}, containing {len(data.get('exercises', []))} exercises")
        
        # Create a Session object to store this workout's history (separate from Workout)
        new_session = Session(
            user_id=current_user.id,
            session_date=datetime.utcnow(),
            duration=str(metrics['duration']) if metrics['duration'] else "0",
            volume=metrics['volume'],
            title=data.get('title', 'Workout'),
            description=data.get('notes', ''),
            session_rating=data.get('rating', 5),
            exp_gained=data.get('exp_gained', 10)  # Default 10 XP if not provided
        )
        
        # Format description
        description = data.get('notes', '')
        if not description and data.get('feeling'):
            description = f"Feeling: {data.get('feeling')}"
        new_session.description = description
        
        db.session.add(new_session)
        db.session.flush()  # Get the session ID
        
        # Now store all completed sets from the workout in the Set model
        formatted_exercises = []
        total_volume = 0
        completed_sets_count = 0
        
        # Get user's latest bodyweight for bodyweight exercises
        latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
            .order_by(Measurement.date.desc()).first()
        user_bodyweight = latest_bodyweight.value if latest_bodyweight else 70  # Default 70kg
        
        if is_imperial and user_bodyweight:
            # Convert bodyweight to kg from lbs if needed
            from .utils import normalize_weight_to_kg
            user_bodyweight = normalize_weight_to_kg(user_bodyweight, 'lbs')
        
        # Process each exercise in the workout
        if 'exercises' in data:
            for exercise_data in data.get('exercises', []):
                ex_id = int(str(exercise_data.get('id')))
                exercise = Exercise.query.get(ex_id)
                
                # If the exercise doesn't exist, skip it
                if not exercise:
                    continue
                
                print(f"Processing {exercise.name} sets")
                exercise_sets = []
                exercise_volume = 0
                
                # Process each set that was completed
                for set_idx, set_data in enumerate(exercise_data.get('sets', [])):
                    if not set_data.get('completed'):
                        continue
                    
                    completed_sets_count += 1
                    
                    # Extract volume if available or calculate it
                    if 'volume' in set_data:
                        set_volume = float(set_data['volume'])
                    else:
                        # Calculate volume based on exercise type
                        set_volume = exercise.calculate_volume(set_data, bodyweight=user_bodyweight, user=current_user)
                    
                    exercise_volume += set_volume
                    total_volume += set_volume
                    
                    exercise_sets.append({
                        'order': set_idx,
                        'type': set_data.get('set_type', 'normal'),
                        'completed': True,
                        'weight': set_data.get('weight'),
                        'reps': set_data.get('reps'),
                        'time': set_data.get('time') or set_data.get('duration'),
                        'distance': set_data.get('distance'),
                        'volume': set_volume
                    })
                    
                    # Create Set record for the exercise history
                    new_set = Set(
                        exercise_id=ex_id,
                        session_id=new_session.id,
                        completed=True,
                        order=set_idx,
                        set_type=set_data.get('set_type', 'normal'),
                        volume=set_volume  # Store the calculated volume
                    )

                    # Add all relevant fields based on exercise type
                    for field in exercise.get_input_fields():
                        if field in set_data:
                            # Get value and convert if needed based on unit preferences
                            value = set_data[field]
                            setattr(new_set, field, value)
                    
                    # Check if set is within range and set the flag
                    if exercise is not None and exercise.range_enabled:
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
                
                # Add formatted exercise data
                formatted_exercises.append({
                    'id': ex_id,
                    'name': exercise.name,
                    'sets': exercise_sets,
                    'volume': exercise_volume
                })
        
        # Update session with total volume and exercise data
        new_session.exercises = json.dumps(formatted_exercises)
        
        # If client provided volume is 0, use our calculated volume
        if new_session.volume == 0:
            new_session.volume = total_volume
        
        # Format duration properly for display
        duration_seconds = data.get('duration', 0)
        if duration_seconds:
            minutes = int(duration_seconds / 60)
            new_session.duration = f"{minutes} minutes"
        
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

@workout.route('/api/routines/public', methods=['GET'])
@login_required
def get_public_routines():
    """Get all public routines"""
    public_routines = Routine.query.filter_by(is_public=True).all()
    
    routines_data = []
    for routine in public_routines:
        # Get user information
        user = User.query.get(routine.user_id)
        username = user.username if user else "Unknown"
        
        # Convert exercises JSON to get count
        try:
            exercises = json.loads(routine.exercises)
            exercise_count = len(exercises) if exercises else 0
        except:
            exercise_count = 0
        
        routines_data.append({
            'id': routine.id,
            'name': routine.name,
            'level': routine.level,
            'goal': routine.goal,
            'muscle_groups': routine.muscle_groups,
            'exercise_count': exercise_count,
            'username': username,
            'view_url': url_for('workout.view_routine', routine_id=routine.id)
        })
    
    return jsonify({'routines': routines_data})

@workout.route('/debug/explore')
@login_required
def debug_explore_page():
    """Debug page for viewing shared routines data"""
    return render_template('workout/debug_explore.html')


@workout.route('/api/routines/explore', methods=['GET'])
@login_required
def explore_routines_api():
    """API endpoint for exploring public routines"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 9, type=int)
        level = request.args.get('level', '')
        goal = request.args.get('goal', '')
        search_query = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'popular')
        
        # Get muscle groups (can be multiple)
        muscle_groups = request.args.getlist('muscle_groups')
        print(f"Searching for muscle groups: {muscle_groups}")
        
        # Base query for shared routines
        query = SharedRoutine.query.filter(SharedRoutine.is_public == True)
        
        # Apply filters
        if level:
            print(f"Filtering by level: {level}")
            query = query.filter(SharedRoutine.level == level)
        
        if goal:
            print(f"Filtering by goal: {goal}")
            query = query.filter(SharedRoutine.goal == goal)
            
        # Apply search filter
        if search_query:
            print(f"Searching for: {search_query}")
            search_terms = f"%{search_query.lower()}%"
            query = query.filter(
                or_(
                    func.lower(SharedRoutine.name).like(search_terms),
                    func.lower(SharedRoutine.description).like(search_terms)
                )
            )
        
        # Apply muscle group filter (must match any of the selected muscles)
        if muscle_groups:
            print(f"Filtering by muscles: {muscle_groups}")
            # Create a list to hold all our OR conditions
            muscle_filters = []
            for muscle in muscle_groups:
                # Try more flexible matching for muscles_worked field
                muscle_filters.append(SharedRoutine.muscles_worked.ilike(f"%{muscle}%"))
                # Also try matching in the data field which may contain exercise details
                muscle_filters.append(SharedRoutine.data.ilike(f"%{muscle}%"))
            
            # Combine with OR logic (routine must contain at least one of the selected muscles)
            query = query.filter(or_(*muscle_filters))
        
        # Apply sorting
        if sort_by == 'newest':
            query = query.order_by(SharedRoutine.created_at.desc())
        elif sort_by == 'name':
            query = query.order_by(SharedRoutine.name.asc())
        else:  # Default: 'popular'
            query = query.order_by(SharedRoutine.copy_count.desc())
        
        # Paginate results
        paginated_routines = query.paginate(page=page, per_page=per_page)
        print(f"Found {paginated_routines.total} routines matching criteria")
        
        # Prepare response data
        response_data = {
            'success': True,
            'routines': [],
            'current_page': page,
            'pages': paginated_routines.pages,
            'total': paginated_routines.total
        }
        
        # Process each routine
        for routine in paginated_routines.items:
            # Get creator info
            creator = User.query.get(routine.user_id) if routine.user_id else None
            
            # Count exercises and extract muscles
            exercise_count = 0
            muscles_worked = []
            
            try:
                if routine.data:
                    routine_data = json.loads(routine.data)
                    
                    # Extract exercise count
                    if 'exercises' in routine_data:
                        exercises = routine_data.get('exercises', [])
                        exercise_count = len(exercises)
                        
                        # Extract muscles from exercises if available
                        for exercise in exercises:
                            if isinstance(exercise, dict):
                                # Try different possible field names for muscles
                                for field in ['muscles_worked', 'primary_muscle', 'exercise_type', 'muscle_group']:
                                    if field in exercise and exercise[field]:
                                        muscle = exercise[field]
                                        if isinstance(muscle, str) and muscle not in muscles_worked:
                                            muscles_worked.append(muscle)
            except Exception as e:
                print(f"Error parsing routine data: {e}")
            
            # Process muscles_worked field from routine itself
            if routine.muscles_worked:
                try:
                    # Try to parse as JSON
                    parsed_muscles = json.loads(routine.muscles_worked)
                    if isinstance(parsed_muscles, list):
                        for muscle in parsed_muscles:
                            if muscle and muscle not in muscles_worked:
                                muscles_worked.append(muscle)
                    elif isinstance(parsed_muscles, str):
                        if parsed_muscles not in muscles_worked:
                            muscles_worked.append(parsed_muscles)
                except:
                    # Fallback to comma-separated string
                    for muscle in routine.muscles_worked.split(','):
                        muscle = muscle.strip()
                        if muscle and muscle not in muscles_worked:
                            muscles_worked.append(muscle)
            
            # Add routine to response
            response_data['routines'].append({
                'id': routine.id,
                'name': routine.name,
                'description': routine.description,
                'level': routine.level,
                'goal': routine.goal,
                'muscles_worked': muscles_worked,
                'exercise_count': exercise_count,
                'copy_count': routine.copy_count,
                'creator': {
                    'username': creator.username if creator else 'Unknown',
                    'badge': creator.badge if creator else 'Beginner'
                } if creator else None
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in explore_routines_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workout.route('/explore/routines/<int:shared_id>')
@login_required
def view_shared_routine(shared_id):
    """View a specific shared routine"""
    shared_routine = SharedRoutine.query.get_or_404(shared_id)
    
    # Get the creator's username
    creator = User.query.get(shared_routine.user_id)
    creator_name = creator.username if creator else "Unknown"
    
    # Parse routine exercises
    exercises = []
    if shared_routine.exercises:
        try:
            routine_exercises = json.loads(shared_routine.exercises)
            for exercise_data in routine_exercises:
                exercise_id = exercise_data.get('id')
                if exercise_id:
                    exercise = Exercise.query.get(exercise_id)
                    if exercise:
                        exercises.append({
                            'id': exercise.id,
                            'name': exercise.name,
                            'muscles_worked': exercise.muscles_worked,
                            'input_type': exercise.input_type,
                            'sets': exercise_data.get('sets', [])
                        })
        except Exception as e:
            print(f"Error parsing shared routine exercises: {str(e)}")
    
    return render_template('workout/view_shared_routine.html', 
                          routine=shared_routine,
                          creator_name=creator_name,
                          exercises=exercises)

@workout.route('/exercise/<int:exercise_id>', methods=['GET'])
@login_required
def view_exercise(exercise_id):
    """Display detailed view of an exercise with history"""
    try:
        # Get the exercise from the database
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Get exercise sets from the database
        sets = Set.query.filter_by(exercise_id=exercise_id).all()
        total_sets = len(sets)
        
        # Process the sets to get statistics
        total_volume = 0
        max_weight = 0
        max_reps = 0
        max_duration = 0
        max_distance = 0
        personal_best = None
        
        # Initialize volume unit based on exercise type
        volume_unit = ""
        if exercise.input_type in ['duration']:
            volume_unit = "seconds"
        elif exercise.input_type in ['weight_reps', 'weighted_bodyweight', 'duration_weight', 'weight_distance']:
            volume_unit = current_user.preferred_weight_unit  # Use the user's preferred unit
        
        for set_obj in sets:
            # Calculate total volume
            if set_obj.volume:
                total_volume += set_obj.volume
            
            # Track max values
            if set_obj.weight and set_obj.weight > max_weight:
                max_weight = set_obj.weight
            
            if set_obj.reps and set_obj.reps > max_reps:
                max_reps = set_obj.reps
                
            if set_obj.time and set_obj.time > max_duration:
                max_duration = set_obj.time
                
            if set_obj.distance and set_obj.distance > max_distance:
                max_distance = set_obj.distance
                
            # Determine personal best based on exercise type
            if not personal_best:
                personal_best = set_obj
            elif exercise.input_type == 'weight_reps' and set_obj.weight and set_obj.reps:
                # For weight_reps, consider weight*reps as the metric
                if (set_obj.weight * set_obj.reps) > (personal_best.weight * personal_best.reps):
                    personal_best = set_obj
            elif exercise.input_type == 'bodyweight_reps' and set_obj.reps:
                # For bodyweight, consider reps as the metric
                if set_obj.reps > personal_best.reps:
                    personal_best = set_obj
            elif exercise.input_type == 'duration' and set_obj.time:
                # For duration, longer is better
                if set_obj.time > personal_best.time:
                    personal_best = set_obj
            elif exercise.input_type == 'duration_weight' and set_obj.weight and set_obj.time:
                # For duration_weight, consider weight*time as the metric
                if (set_obj.weight * set_obj.time) > (personal_best.weight * personal_best.time):
                    personal_best = set_obj
            elif exercise.input_type == 'distance_duration' and set_obj.distance:
                # For distance_duration, longer distance is better
                if set_obj.distance > personal_best.distance:
                    personal_best = set_obj
        
        # Calculate estimated 1RM if this is a weight/reps exercise
        one_rep_max = None
        if exercise.input_type == 'weight_reps' and max_weight and max_reps:
            # Brzycki formula: 1RM = weight × (36 / (37 - reps))
            if max_reps < 37:  # Formula breaks down at 37+ reps
                one_rep_max = max_weight * (36 / (37 - max_reps))
                
        print(f"Rendering exercise view with {total_sets} sets, total volume: {total_volume} {volume_unit}")
        
        # Prepare trend data for charts
        trend_data = prepare_exercise_trend_data(exercise_id)
        
        # Get sessions where this exercise was used
        sessions = db.session.query(Session)\
            .join(Set, Set.session_id == Session.id)\
            .filter(Set.exercise_id == exercise_id)\
            .order_by(Session.session_date.desc())\
            .distinct().all()
            
        # Format session data for display
        session_data = []
        for session in sessions:
            session_sets = db.session.query(Set)\
                .filter(Set.session_id == session.id, Set.exercise_id == exercise_id)\
                .all()
                
            session_volume = sum(s.volume or 0 for s in session_sets)
            
            session_data.append({
                'id': session.id,
                'date': session.session_date.strftime('%Y-%m-%d'),
                'title': session.title,
                'sets': len(session_sets),
                'volume': session_volume
            })
        
        # Prepare statistics for the template
        stats = {
            'total_volume': total_volume,
            'max_weight': max_weight,
            'max_reps': max_reps,
            'max_duration': max_duration,
            'max_distance': max_distance,
            'one_rm': round(one_rep_max, 1) if one_rep_max else None,
            'volume_unit': volume_unit
        }
        
        return render_template('workout/view_exercise.html',
                               exercise=exercise,
                               sets=sets,
                               total_sets=total_sets,
                               stats=stats,
                               trend_data=trend_data,
                               session_data=session_data)
    except Exception as e:
        print(f"Error viewing exercise: {str(e)}")
        return jsonify({'error': str(e)}), 500

@workout.route('/api/workout/create-exercise', methods=['POST'])
@login_required
def create_exercise_api():
    """Create a new exercise"""
    try:
        # Debug the incoming request
        print("Received create exercise request")
        
        # Check if the request has JSON content
        if not request.is_json:
            print("Request does not contain JSON")
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Required fields
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'error': 'Exercise name is required'}), 400
        
        # Create new exercise
        new_exercise = Exercise(
            name=name,
            equipment=data.get('equipment', ''),
            muscles_worked=data.get('muscles_worked', ''),
            exercise_type=data.get('exercise_type', ''),
            input_type=data.get('input_type', 'weight_reps'),
            user_created=True,
            created_by=current_user.id
        )
        
        # Add to database
        db.session.add(new_exercise)
        db.session.commit()
        
        print(f"Successfully created exercise: {new_exercise.id} - {new_exercise.name}")
        
        return jsonify({
            'success': True,
            'exercise': {
                'id': new_exercise.id,
                'name': new_exercise.name,
                'equipment': new_exercise.equipment,
                'muscles_worked': new_exercise.muscles_worked,
                'input_type': new_exercise.input_type
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating exercise: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to create exercise: {str(e)}'}), 500

@workout.route('/exercise/create', methods=['GET'])
@login_required
def create_exercise_page():
    """Page for creating a new exercise"""
    # Constants for form selections
    equipment_options = [
        'Barbell', 'Dumbbell', 'Body Weight', 'Cable Machine', 'Leverage Machine',
        'EZ Bar', 'Trap Bar', 'Smith Machine', 'Weighted', 'Battling Rope',
        'Medicine Ball', 'Kettlebell', 'Sled Machine', 'Band', 'Bosu Ball',
        'Power Sled', 'Resistance Band', 'Roll', 'Roll Ball', 'Rope',
        'Stability Ball', 'Suspension', 'Wheel Roller'
    ]
    
    body_parts = [
        'Chest', 'Biceps', 'Triceps', 'Abs', 'Hips', 'Quadriceps',
        'Hamstrings', 'Back', 'Shoulders', 'Forearms', 'Calves', 'Neck', 'Cardio'
    ]
    
    muscles = [
        'Abdominals', 'Abductors', 'Adductors', 'Biceps', 'Calves', 'Cardio',
        'Chest', 'Forearms', 'Full Body', 'Glutes', 'Hamstrings', 'Lats',
        'Lower Back', 'Neck', 'Quadriceps', 'Shoulders', 'Traps', 'Triceps',
        'Upper Back', 'Other'
    ]
    
    input_types = [
        {'value': 'weight_reps', 'label': 'Weight & Reps'},
        {'value': 'bodyweight_reps', 'label': 'Bodyweight & Reps'},
        {'value': 'weighted_bodyweight', 'label': 'Weighted Bodyweight & Reps'},
        {'value': 'assisted_bodyweight', 'label': 'Assisted Bodyweight & Reps'},
        {'value': 'duration', 'label': 'Duration Only'},
        {'value': 'duration_weight', 'label': 'Duration & Weight'},
        {'value': 'distance_duration', 'label': 'Distance & Duration'},
        {'value': 'weight_distance', 'label': 'Weight & Distance'}
    ]
    
    return render_template(
        'workout/create_exercise.html',
        equipment_options=equipment_options,
        body_parts=body_parts,
        muscles=muscles,
        input_types=input_types
    )

@workout.route('/create-exercise', methods=['POST'])
@login_required
def create_exercise():
    """Create a new exercise"""
    return create_exercise_api()

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

def prepare_exercise_trend_data(exercise_id):
    """
    Prepare trend data for exercise charts.
    Returns JSON-serializable data for charts with dates, volume, weight, reps, etc.
    """
    try:
        # Get the exercise
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Get user's previous sets for this exercise
        previous_sets = []
        
        if current_user.is_authenticated:
            # Find sets from recent workouts - get more data for better graphs
            previous_sets_query = (
                Set.query
                .join(Session)
                .filter(
                    Set.exercise_id == exercise_id,
                    Session.user_id == current_user.id,
                    Set.completed == True  # Only get completed sets
                )
                .order_by(Session.session_date.asc()) # Sort chronologically for graphs
                .limit(50)
            )
            
            previous_sets = previous_sets_query.all()
        
        # Group sets by date for trend analysis
        grouped_sets = {}
        
        for set_data in previous_sets:
            try:
                # Extract date (just the day)
                date_key = set_data.session.session_date.strftime('%Y-%m-%d')
                
                # Initialize date entry if not exists
                if date_key not in grouped_sets:
                    grouped_sets[date_key] = {
                        'display_date': set_data.session.session_date.strftime('%b %d'),
                        'complete_date': set_data.session.session_date,
                        'sets': 0,
                        'volume': 0,
                        'weight': 0,  # For max weight
                        'reps': 0,    # Total reps
                        'duration': 0, # Total duration
                        'distance': 0, # Total distance
                        'additional_weight': 0, # For weighted bodyweight
                        'assistance_weight': 0  # For assisted exercises
                    }
                
                # Update daily stats
                day_stats = grouped_sets[date_key]
                day_stats['sets'] += 1
                
                # Update metrics based on exercise type
                if exercise.input_type == 'weight_reps':
                    # Update reps
                    if set_data.reps:
                        day_stats['reps'] += set_data.reps
                
                    # Update max weight
                    if set_data.weight and set_data.weight > day_stats['weight']:
                        day_stats['weight'] = set_data.weight
                    
                    # Update volume
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'bodyweight_reps':
                    # Update reps
                    if set_data.reps:
                        day_stats['reps'] += set_data.reps
                        
                    # Use set volume if available
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'weighted_bodyweight':
                    # Update reps
                    if set_data.reps:
                        day_stats['reps'] += set_data.reps
                        
                    # Update additional weight max
                    if set_data.additional_weight and set_data.additional_weight > day_stats['additional_weight']:
                        day_stats['additional_weight'] = set_data.additional_weight
                        
                    # Use set volume if available
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'assisted_bodyweight':
                    # Update reps
                    if set_data.reps:
                        day_stats['reps'] += set_data.reps
                        
                    # Update assistance weight (lower is better)
                    if set_data.assistance_weight:
                        if day_stats['assistance_weight'] == 0 or set_data.assistance_weight < day_stats['assistance_weight']:
                            day_stats['assistance_weight'] = set_data.assistance_weight
                        
                    # Use set volume if available
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'duration':
                    # Track duration
                    if set_data.time:
                        time_value = set_data.time
                        day_stats['duration'] += time_value
                        
                        # For duration-only exercises, time is the volume metric
                        day_stats['volume'] += time_value
                    elif set_data.volume:
                        # Fallback to stored volume
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'duration_weight':
                    # Track duration
                    if set_data.time:
                        time_value = set_data.time
                        day_stats['duration'] += time_value
                        
                    # Track weight
                    if set_data.weight and set_data.weight > day_stats['weight']:
                        day_stats['weight'] = set_data.weight
                        
                    # Calculate volume
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'distance_duration':
                    # Track distance
                    if set_data.distance:
                        distance_value = set_data.distance
                        day_stats['distance'] += distance_value
                        
                    # Track duration
                    if set_data.time:
                        time_value = set_data.time
                        day_stats['duration'] += time_value
                        
                    # For distance exercises, volume can be distance * time
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
                        
                elif exercise.input_type == 'weight_distance':
                    # Track weight
                    if set_data.weight:
                        weight_value = set_data.weight
                        if weight_value > day_stats['weight']:
                            day_stats['weight'] = weight_value
                        
                    # Track distance
                    if set_data.distance:
                        distance_value = set_data.distance
                        day_stats['distance'] += distance_value
                        
                    # For weight_distance, volume is weight * distance
                    if set_data.volume:
                        day_stats['volume'] += set_data.volume
            except Exception as e:
                print(f"Error processing set for trend data: {str(e)}")
                continue
        
        # Sort grouped sets by date
        sorted_days = sorted(grouped_sets.values(), key=lambda x: x['complete_date']) if grouped_sets else []
        
        # Prepare trend data safely
        trend_data = {
            'dates': [day['display_date'] for day in sorted_days],
            'volume': [day['volume'] for day in sorted_days],
            'weight': [day['weight'] for day in sorted_days],
            'reps': [day['reps'] for day in sorted_days],
            'duration': [day['duration'] for day in sorted_days],
            'distance': [day['distance'] for day in sorted_days],
            'additional_weight': [day['additional_weight'] for day in sorted_days],
            'assistance_weight': [day['assistance_weight'] for day in sorted_days],
        }
        
        return json.dumps(trend_data)
    except Exception as e:
        print(f"Error preparing exercise trend data: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps({
            'dates': [],
            'volume': [],
            'weight': [],
            'reps': [],
            'duration': [],
            'distance': [],
            'additional_weight': [],
            'assistance_weight': [],
        })