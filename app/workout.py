from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Exercise, Session, User, Measurement, Set, Routine, Workout, WorkoutExercise, WorkoutSet
from . import db
import json
from datetime import datetime, timedelta, time

workout = Blueprint('workout', __name__)

@workout.route('/start-workout')
@login_required
def start_workout():
    """
    This route shows the workout creation page where users can
    select exercises and start logging their workout.
    """
    # Get all available exercises
    exercises = Exercise.query.all()
    
    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    user_weight = latest_bodyweight.value if latest_bodyweight else None
    
    return render_template('workout/start.html', exercises=exercises, user_weight=user_weight)

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
                    set_type=set_data.get('set_type', 'normal')
                )

                # Add all relevant fields based on exercise type
                for field in exercise.get_input_fields():
                    setattr(new_set, field, set_data.get(field, 0))
                
                # Check if set is within range and set the flag
                if exercise.range_enabled:
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

@workout.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """
    This route shows the detailed view of a completed workout session.
    It includes all exercise data, stats, and progress comparisons.
    """
    print(f"Viewing session {session_id}")
    
    # Try to find the workout in the Workout database
    workout = Workout.query.get(session_id)
    
    if workout:
        print(f"Found workout with ID {session_id}")
        # Check if user has permission to view this workout
        if workout.user_id != current_user.id:
            # Check if the workout is from a user that the current user follows
            creator = User.query.get(workout.user_id)
            if creator and creator.privacy_setting == 'private' and creator.id not in [u.id for u in current_user.following]:
                flash('You do not have permission to view this workout.')
                return redirect(url_for('workout.workout_page'))
        
        # Ensure necessary attributes for template compatibility
        if not hasattr(workout, 'session_date'):
            workout.session_date = workout.date
            
        if not hasattr(workout, 'session_rating'):
            workout.session_rating = workout.rating
            
        # Parse exercises data
        exercises = []
        
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
        if not exercises and workout.data:
            try:
                data = json.loads(workout.data)
                exercises_data = data.get('exercises', [])
                
                for exercise_data in exercises_data:
                    if exercise_data.get('sets'):
                        completed_sets = [s for s in exercise_data.get('sets', []) if s.get('completed')]
                        
                        if completed_sets:
                            exercise = {
                                'name': exercise_data.get('name', 'Unknown Exercise'),
                                'sets': len(completed_sets)
                            }
                            
                            # Add type-specific fields
                            if exercise_data.get('input_type') == 'weight_reps':
                                weights = [s.get('weight', 0) for s in completed_sets if s.get('weight')]
                                reps = [s.get('reps', 0) for s in completed_sets if s.get('reps')]
                                
                                if weights and reps:
                                    exercise['weight'] = round(sum(weights) / len(weights), 1)
                                    exercise['reps'] = round(sum(reps) / len(reps))
                            
                            exercises.append(exercise)
            except Exception as e:
                print(f"Error parsing workout exercises from data: {e}")
        
        print(f"Returning workout with {len(exercises)} exercises")
        return render_template('workout/view_session.html', 
                              session=workout, 
                              exercises=exercises)
    
    # Fall back to Session model for backwards compatibility
    session = Session.query.get_or_404(session_id)
    print(f"Found legacy session with ID {session_id}")
    
    # Check if user has permission to view this session
    if session.user.privacy_setting == 'private' and session.user_id != current_user.id:
        flash('You do not have permission to view this session.')
        return redirect(url_for('auth.home'))
    
    # Parse exercises from JSON
    try:
        exercises = json.loads(session.exercises) if session.exercises else []
    except Exception as e:
        print(f"Error parsing session exercises: {e}")
        exercises = []
    
    print(f"Returning legacy session with {len(exercises)} exercises")
    return render_template('workout/view_session.html', 
                          session=session, 
                          exercises=exercises)

@workout.route('/api/exercises')
@login_required
def get_exercises():
    exercises = Exercise.query.all()
    return jsonify([{
        'id': e.id,
        'name': e.name,
        'muscles_worked': e.muscles_worked
    } for e in exercises])

@workout.route('/api/exercise-details/<int:exercise_id>')
@login_required
def get_exercise_details(exercise_id):
    try:
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Get the exercise details
        exercise_data = {
            'id': exercise.id,
            'name': exercise.name,
            'muscles_worked': exercise.muscles_worked,
            'input_type': exercise.input_type,
            'range_enabled': exercise.range_enabled,
            'min_reps': exercise.min_reps,
            'max_reps': exercise.max_reps,
            'min_duration': exercise.min_duration,
            'max_duration': exercise.max_duration,
            'min_distance': exercise.min_distance,
            'max_distance': exercise.max_distance,
            'rest_duration': exercise.rest_duration,
            'previousSets': []
        }
        
        # First, try to get previous sets from Session/Set records
        try:
            # Get the last completed session with this exercise
            most_recent_session = db.session.query(Session)\
                .join(Set)\
                .filter(
                    Session.user_id == current_user.id,
                    Set.exercise_id == exercise_id,
                    Set.completed == True
                )\
                .order_by(Session.session_date.desc())\
                .first()
                
            if most_recent_session:
                previous_sets = Set.query\
                    .filter(
                        Set.session_id == most_recent_session.id,
                        Set.exercise_id == exercise_id,
                        Set.completed == True
                    )\
                    .order_by(Set.order)\
                    .all()
                    
                print(f"Found {len(previous_sets)} previous sets for exercise {exercise_id} from sessions")
                
                # Convert Set objects to dictionaries
                for set_obj in previous_sets:
                    set_data = {
                        'weight': set_obj.weight,
                        'reps': set_obj.reps,
                        'duration': set_obj.duration,
                        'distance': set_obj.distance,
                        'additional_weight': set_obj.additional_weight,
                        'assistance_weight': set_obj.assistance_weight,
                        'time': set_obj.time,
                        'completed': True,
                        'set_type': set_obj.set_type or 'normal',
                        'order': set_obj.order
                    }
                    exercise_data['previousSets'].append(set_data)
        except Exception as e:
            print(f"Error fetching previous sets from sessions: {str(e)}")
        
        # If no sets found, try recent Workout records as fallback
        if not exercise_data['previousSets']:
            try:
                # Get previous sets for this exercise (from the most recent workout)
                recent_workout = (
                    Workout.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Workout.date.desc())
                    .first()
                )
                
                if recent_workout and recent_workout.data:
                    try:
                        workout_data = json.loads(recent_workout.data)
                        for exercise_entry in workout_data.get('exercises', []):
                            if exercise_entry.get('id') and int(str(exercise_entry.get('id'))) == exercise_id:
                                # Found matching exercise, extract the sets
                                for set_data in exercise_entry.get('sets', []):
                                    if set_data.get('completed'):
                                        exercise_data['previousSets'].append(set_data)
                                break
                        print(f"Found {len(exercise_data['previousSets'])} previous sets for exercise {exercise_id} from workout data")
                    except Exception as e:
                        # Handle any JSON parsing errors
                        print(f"Error parsing workout data: {str(e)}")
            except Exception as e:
                print(f"Error fetching recent workout: {str(e)}")
        
        return jsonify(exercise_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in get_exercise_details: {str(e)}")
        return jsonify({
            'error': f"Failed to get exercise details: {str(e)}",
            'id': exercise_id,
            'name': "Unknown Exercise",
            'muscles_worked': "",
            'input_type': "weight_reps",
            'range_enabled': False,
            'previousSets': []
        }), 200  # Return 200 with error info instead of 500

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
        if unit == 'lbs':
            value = value * 0.45359237  # Convert to kg
        elif unit == 'in':
            value = value * 2.54  # Convert to cm
            
        # Validate converted value
        if value < valid_types[measurement_type]['min'] or value > valid_types[measurement_type]['max']:
            return jsonify({
                'success': False, 
                'error': f"Value must be between {valid_types[measurement_type]['min']} and {valid_types[measurement_type]['max']} {valid_types[measurement_type]['unit']}"
            }), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid value'}), 400
    
    # Create new measurement
    log = Measurement(
        user_id=current_user.id,
        type=measurement_type,
        value=value,
        unit=valid_types[measurement_type]['unit'],
        date=datetime.utcnow()
    )
    
    db.session.add(log)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

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
        if exercise.range_enabled:
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
    
    # Update the routine
    routine.name = data.get('name')
    routine.level = data.get('level', routine.level)
    routine.goal = data.get('goal', routine.goal)
    routine.muscle_groups = ','.join(data.get('muscle_groups', []))
    routine.description = data.get('description', '')
    routine.is_public = data.get('is_public', False)
    routine.exercises = json.dumps(data.get('exercises', []))
    routine.updated_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({'success': True})

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
def explore_routines():
    """Get public routines for exploration"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Optional filters
    level = request.args.get('level')
    goal = request.args.get('goal')
    muscle_group = request.args.get('muscle_group')
    
    query = Routine.query.filter_by(is_public=True)
    
    # Apply filters if provided
    if level:
        query = query.filter_by(level=level)
    if goal:
        query = query.filter_by(goal=goal)
    if muscle_group:
        query = query.filter(Routine.muscle_groups.like(f'%{muscle_group}%'))
        
    # Exclude user's own routines
    query = query.filter(Routine.user_id != current_user.id)
    
    # Paginate results
    paginated_routines = query.order_by(Routine.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Get creators for each routine
    routine_data = []
    for routine in paginated_routines.items:
        creator = User.query.get(routine.user_id)
        routine_dict = routine.to_dict()
        routine_dict['creator'] = {
            'id': creator.id,
            'username': creator.username
        }
        routine_data.append(routine_dict)
    
    return jsonify({
        'success': True,
        'routines': routine_data,
        'total': paginated_routines.total,
        'pages': paginated_routines.pages,
        'current_page': page
    })

@workout.route('/api/routines/<int:routine_id>/copy', methods=['POST'])
@login_required
def copy_routine(routine_id):
    """Copy a public routine to user's routines"""
    routine = Routine.query.get_or_404(routine_id)
    
    # Check if routine is public or owned by user
    if not routine.is_public and routine.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to copy this routine'
        }), 403
        
    try:
        # Create a copy of the routine for the current user
        new_routine = Routine(
            name=f"{routine.name} (Copy)",
            level=routine.level,
            goal=routine.goal,
            muscle_groups=routine.muscle_groups,
            exercises=routine.exercises,
            is_public=False,  # Default to private for copied routines
            description=routine.description,
            user_id=current_user.id
        )
        
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
        # Mark workout as completed
        workout.completed = True
        workout.end_time = datetime.utcnow()
        
        # Calculate duration in seconds
        if workout.start_time:
            duration = (workout.end_time - workout.start_time).total_seconds()
            workout.duration = int(duration)
        
        # Save any notes
        if 'notes' in data:
            workout.notes = data['notes']
        
        # Calculate total volume if applicable
        total_volume = 0
        for we in workout.exercises:
            for s in we.sets:
                if s.completed:
                    # Calculate volume based on exercise type
                    if s.weight and s.reps:
                        total_volume += s.weight * s.reps
                    elif s.weight and s.distance:
                        total_volume += s.weight * s.distance
        
        workout.total_volume = total_volume
        
        # Award XP to the user
        # Base XP for workout
        exp_gained = 10
        
        # Additional XP based on completed sets
        completed_sets = 0
        for we in workout.exercises:
            completed_sets += sum(1 for s in we.sets if s.completed)
        
        exp_gained += completed_sets * 3
        
        # Additional XP for workout duration
        if workout.duration:
            # Extra XP for every 10 minutes
            exp_gained += (workout.duration // 600) * 5
        
        # Update user stats
        current_user.exp += exp_gained
        current_user.update_level()
        
        # Update streak if it's a new day
        # (This is a simplified implementation, you might want to expand it)
        today = datetime.now().date()
        last_workout_date = None
        
        # Find the date of the last workout
        last_workout = Workout.query.filter_by(
            user_id=current_user.id, 
            completed=True
        ).order_by(Workout.end_time.desc()).first()
        
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
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Workout completed successfully',
            'exp_gained': exp_gained,
            'new_streak': current_user.streak
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error completing workout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to complete workout'
        }), 500

@workout.route('/api/log-workout', methods=['POST'])
@login_required
def log_workout_api():
    """Log a completed workout"""
    # Start with debug information
    print("=== log_workout_api called ===")
    db_session = db.session
    
    try:
        # Get and log request data
        data = request.get_json()
        print(f"Request data type: {type(data)}")
        
        if not data:
            print("Error: No data received in request")
            return jsonify({
                'success': False,
                'error': "No data received"
            }), 400
        
        # Log data keys for debugging
        print(f"Data keys: {list(data.keys())}")
        print(f"Exercises count: {len(data.get('exercises', []))}")
        
        # Get required data with fallbacks
        title = data.get('title', f"Workout - {datetime.now().strftime('%Y-%m-%d')}")
        
        # Handle both 'notes' and 'description' field variations
        description = data.get('description', '')
        if not description:
            description = data.get('notes', '')  # Backward compatibility
        
        # Parse numeric values safely
        try:
            rating = int(data.get('rating', 3))
        except (ValueError, TypeError):
            rating = 3
            print("Warning: Invalid rating value, using default")
            
        try:
            duration = int(data.get('duration', 0))
        except (ValueError, TypeError):
            duration = 0
            print("Warning: Invalid duration value, using default")
        
        # Format duration for display (convert seconds to minutes)
        formatted_duration = f"{duration // 60} minutes" if duration > 0 else "0 minutes"
        
        # Parse volume, reps, sets
        try:
            volume = float(data.get('volume', 0))
        except (ValueError, TypeError):
            volume = 0
            print("Warning: Invalid volume value, using default")
            
        try:
            total_reps = int(data.get('total_reps', 0))
        except (ValueError, TypeError):
            total_reps = 0
            print("Warning: Invalid total_reps value, using default")
            
        try:
            sets_completed = int(data.get('sets_completed', 0))
        except (ValueError, TypeError):
            sets_completed = 0
            print("Warning: Invalid sets_completed value, using default")
            
        try:
            exp_gained = int(data.get('exp_gained', 0))
        except (ValueError, TypeError):
            exp_gained = 0
            print("Warning: Invalid exp_gained value, using default")
            
        try:
            routine_id = int(data.get('routine_id', 0)) or None
        except (ValueError, TypeError):
            routine_id = None
            print("Warning: Invalid routine_id value, using None")
            
        print(f"Creating workout with title: '{title}', duration: {duration}s")
        
        # Create the workout record
        workout = Workout(
            user_id=current_user.id,
            title=title,
            notes=description,  # Make sure we're using the resolved value
            rating=rating,
            date=datetime.now(),
            duration=duration,
            data=json.dumps(data),
            routine_id=routine_id,
            volume=volume,
            total_reps=total_reps,
            sets_completed=sets_completed,
            exp_gained=exp_gained
        )
        
        db_session.add(workout)
        db_session.flush()  # Get workout.id
        print(f"Workout created with ID: {workout.id}")
        
        # Calculate total volume and prepare exercise summary for display
        formatted_exercises = []
        
        # Process each exercise
        for exercise_data in data.get('exercises', []):
            try:
                if not exercise_data.get('id'):
                    print(f"Warning: Exercise missing ID: {exercise_data}")
                    continue
                    
                # Get basic exercise info
                exercise_id = exercise_data.get('id')
                if isinstance(exercise_id, str) and exercise_id.isdigit():
                    exercise_id = int(exercise_id)
                    
                exercise = Exercise.query.get(exercise_id)
                if not exercise:
                    print(f"Warning: Exercise with ID {exercise_id} not found")
                    continue
                
                # Count completed sets
                completed_sets = [s for s in exercise_data.get('sets', []) if s.get('completed')]
                if not completed_sets:
                    print(f"Warning: No completed sets for exercise {exercise.name}")
                    continue
                
                print(f"Processing exercise: {exercise.name} with {len(completed_sets)} completed sets")
                
                # Format exercise for display
                formatted_exercise = {
                    'name': exercise.name,
                    'sets': len(completed_sets)
                }
                
                formatted_exercises.append(formatted_exercise)
                print(f"Formatted exercise: {formatted_exercise}")
                
            except Exception as ex:
                print(f"Error processing exercise: {ex}")
                continue
        
        # Store the formatted exercise data
        try:
            # Also create a session entry for backward compatibility
            session = Session(
                user_id=current_user.id,
                session_date=datetime.now(),
                duration=formatted_duration,
                volume=int(volume),
                exercises=json.dumps(formatted_exercises),
                session_rating=rating,
                title=title,
                description=description,
                sets_completed=sets_completed,
                total_reps=total_reps,
                exp_gained=exp_gained
            )
            
            db_session.add(session)
            db_session.flush()
            print(f"Legacy session created with ID: {session.id}")
            
        except Exception as ex:
            print(f"Error creating legacy session: {ex}")
            # Continue anyway - the workout is the primary record
        
        # Update user streak
        try:
            user = current_user
            last_workout = Workout.query.filter_by(user_id=user.id).order_by(Workout.date.desc()).offset(1).first()
            
            today = datetime.now().date()
            
            # Update current streak safely
            if not hasattr(user, 'current_streak'):
                # If the current_streak attribute is missing, use the streak attribute instead
                if not last_workout:
                    user.streak = 1
                    print("First workout, setting streak=1")
                else:
                    last_workout_date = last_workout.date.date()
                    days_since_last = (today - last_workout_date).days
                    
                    if days_since_last <= 1:  # Same day or consecutive day workout
                        user.streak += 1
                        print(f"Consecutive day workout, streak increased to {user.streak}")
                    elif days_since_last > 1:  # Streak broken
                        user.streak = 1
                        print(f"Streak broken after {days_since_last} days, reset to 1")
            else:
                # Use current_streak attribute if it exists
                if not last_workout:
                    user.current_streak = 1
                    print("First workout, setting current_streak=1")
                else:
                    last_workout_date = last_workout.date.date()
                    days_since_last = (today - last_workout_date).days
                    
                    if days_since_last <= 1:  # Same day or consecutive day workout
                        user.current_streak += 1
                        print(f"Consecutive day workout, current_streak increased to {user.current_streak}")
                    elif days_since_last > 1:  # Streak broken
                        user.current_streak = 1
                        print(f"Streak broken after {days_since_last} days, current_streak reset to 1")
        except Exception as streak_error:
            print(f"Error updating streak: {streak_error}")
        
        # Update user EXP if not already provided
        try:
            if not exp_gained:
                daily_bonus = 0
                streak_bonus = 0
                
                # Fallback: Assign 10 XP per minute, capped at 3 hours (1800 XP)
                base_exp = min(duration / 60 * 10, 1800)
                
                # Check if user already worked out today
                today_workout = Workout.query.filter(
                    Workout.user_id == user.id,
                    Workout.date >= datetime.combine(today, time.min),
                    Workout.date <= datetime.combine(today, time.max),
                    Workout.id != workout.id  # Exclude current workout
                ).first()
                
                if not today_workout:
                    daily_bonus = 100  # Bonus for first workout of the day
                    print("First workout today, adding 100 XP daily bonus")
                
                # Streak bonus: +20 XP per day in streak
                streak_value = getattr(user, 'current_streak', user.streak)
                if streak_value > 1:
                    streak_bonus = 20 * streak_value
                    print(f"Streak bonus: +{streak_bonus} XP for {streak_value} day streak")
                
                total_exp = int(base_exp + daily_bonus + streak_bonus)
                
                # Only set exp_gained if it wasn't provided
                workout.exp_gained = total_exp
                if hasattr(session, 'id'):  # Make sure session was created
                    session.exp_gained = total_exp
                
                print(f"Total XP calculated: {total_exp} (base: {base_exp}, daily: {daily_bonus}, streak: {streak_bonus})")
            else:
                # Use the provided exp_gained value
                total_exp = exp_gained
                print(f"Using provided exp_gained: {total_exp}")
            
            # Add EXP to user
            user.exp += total_exp
            print(f"Added {total_exp} XP to user (new total: {user.exp})")
        except Exception as exp_error:
            print(f"Error calculating XP: {exp_error}")
        
        # Check for level up
        level_up = False
        new_level = 0
        try:
            # Use update_level method to handle level progression
            level_info = user.update_level()
            level_up = level_info.get('leveled_up', False)
            new_level = level_info.get('new_level', user.level)
            
            if level_up:
                print(f"User leveled up to level {new_level}!")
            else:
                print(f"No level up. User remains at level {user.level}")
        except Exception as level_error:
            print(f"Error updating level: {level_error}")
        
        # Save all changes
        try:
            db_session.commit()
            print("Successfully saved workout and updated user stats")
        except Exception as commit_error:
            db_session.rollback()
            raise commit_error
        
        # Return success response with combined data
        response_data = {
            'success': True,
            'workout_id': workout.id,
            'exp_gained': total_exp,
            'level': user.level,
            'streak': getattr(user, 'current_streak', user.streak)
        }
        
        # Add session ID for backward compatibility
        if 'session' in locals() and hasattr(session, 'id'):
            response_data['session_id'] = session.id
        else:
            # If session wasn't created, use workout ID as fallback
            response_data['session_id'] = workout.id
            
        # Add level up info
        if level_up:
            # Disable level up notifications - just log server-side
            print(f"User leveled up to level {new_level} (notification disabled)")
            # Don't add to response
            # response_data['level_up'] = True
            # response_data['new_level'] = new_level
            # response_data['next_level_exp'] = user.next_level_exp
            
        return jsonify(response_data)
        
    except Exception as e:
        # If any error occurred, roll back the transaction
        if 'db_session' in locals():
            db_session.rollback()
        
        # Log detailed error information
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in log_workout_api: {str(e)}")
        print(f"Error details: {error_details}")
        
        # Return a user-friendly error message
        return jsonify({
            'success': False,
            'error': f"Failed to save workout: {str(e)}"
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